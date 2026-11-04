import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_WEB_URL = "https://app.zipnova.com.ar"
WEB_URL_PARAM = "zipnova_balance.web_url"


class ZipnovaAccountBalance(models.Model):
    _name = "zipnova.account.balance"
    _description = "Zipnova Account Balance"
    _order = "company_id"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, ondelete="cascade", index=True
    )
    account_id = fields.Char(string="Zipnova Account ID", readonly=True)
    credit_limit_currency = fields.Char(string="Currency", readonly=True)
    balance = fields.Float(string="Current Balance (Debt)", readonly=True, digits=(16, 2))
    credit_limit = fields.Float(readonly=True, digits=(16, 2))
    available = fields.Float(string="Available Credit", readonly=True, digits=(16, 2))
    last_update = fields.Datetime(string="Last Update", readonly=True)
    last_error = fields.Text(readonly=True)
    state = fields.Selection(
        [("ok", "OK"), ("error", "Error")], readonly=True, default="error"
    )

    _sql_constraints = [
        ("company_uniq", "unique(company_id)", "Only one Zipnova balance per company."),
    ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _to_float(self, value):
        if value in (None, False, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @api.model
    def _get_or_create(self, company):
        record = self.sudo().search([("company_id", "=", company.id)], limit=1)
        if not record:
            record = self.sudo().create({"company_id": company.id})
        return record

    @api.model
    def _fetch_billing(self, company):
        """Return a dict of values to write. Never raises."""
        mixin = self.env["zipnova.api.mixin"]
        now = fields.Datetime.now()
        try:
            mixin._zipnova_check_credentials(company)
            account_id = mixin._zipnova_account_id(company)
            status, data, _raw = mixin._zipnova_request(
                company, "GET", "/accounts/%s/billing" % account_id
            )
        except UserError as err:
            return {"state": "error", "last_error": str(err.args[0] if err.args else err),
                    "last_update": now}
        except Exception as err:  # pylint: disable=broad-except
            _logger.exception("Zipnova billing refresh failed for %s", company.name)
            return {"state": "error", "last_update": now,
                    "last_error": _("Unexpected error querying Zipnova: %s") % err}
        if status >= 400:
            return {"state": "error", "last_update": now,
                    "last_error": mixin._zipnova_error_message(status, data)}
        if not isinstance(data, dict):
            return {"state": "error", "last_update": now,
                    "last_error": _("Zipnova returned an invalid (non JSON) response.")}
        return {
            "state": "ok",
            "last_error": False,
            "last_update": now,
            "account_id": str(data.get("account_id") or account_id),
            "balance": self._to_float(data.get("balance")),
            "credit_limit": self._to_float(data.get("credit_limit")),
            "credit_limit_currency": data.get("credit_limit_currency") or False,
            "available": self._to_float(data.get("available")),
        }

    @api.model
    def _refresh_company(self, company):
        record = self._get_or_create(company)
        record.sudo().write(self._fetch_billing(company))
        return record

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_refresh(self):
        for record in self:
            self._refresh_company(record.company_id)
        return True

    @api.model
    def action_open_balance(self):
        record = self._refresh_company(self.env.company)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "oo_zipnova_balance.action_zipnova_account_balance"
        )
        action.update({"res_id": record.id, "view_mode": "form",
                       "views": [(False, "form")]})
        return action

    def action_open_zipnova_web(self):
        url = (
            self.env["ir.config_parameter"].sudo().get_param(WEB_URL_PARAM)
            or DEFAULT_WEB_URL
        )
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    @api.model
    def _cron_refresh_balances(self):
        """One request per company (no pagination): isolate each company with
        its own try/except and commit so one failure does not undo the rest."""
        companies = self.env["res.company"].sudo().search([("zipnova_id", "!=", False)])
        for company in companies:
            try:
                self._refresh_company(company)
                if not self.env.registry.in_test_mode():
                    self.env.cr.commit()  # pylint: disable=invalid-commit
            except Exception:  # pylint: disable=broad-except
                self.env.cr.rollback()
                _logger.exception("Zipnova balance cron failed for %s", company.name)
