from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

MIXIN = "odoo.addons.zipnova.models.zipnova_api.ZipnovaApiMixin"


@tagged("post_install", "-at_install")
class TestZipnovaAccountBalance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.sudo().write(
            {"zipnova_id": "1234", "zipnova_key": "k", "zipnova_secret": "s"}
        )
        cls.Balance = cls.env["zipnova.account.balance"]

    def _refresh(self, result):
        with patch(MIXIN + "._zipnova_request", return_value=result) as mock:
            record = self.Balance._refresh_company(self.company)
        return record, mock

    def test_refresh_ok(self):
        data = {"account_id": 1234, "balance": "1500.50", "credit_limit": 10000,
                "credit_limit_currency": "ARS", "available": 8499.5}
        record, mock = self._refresh((200, data, b"{}"))
        self.assertEqual(mock.call_args.args[2], "/accounts/1234/billing")
        self.assertEqual(record.state, "ok")
        self.assertAlmostEqual(record.balance, 1500.50)
        self.assertEqual(record.credit_limit_currency, "ARS")
        self.assertAlmostEqual(record.available, 8499.5)
        self.assertFalse(record.last_error)
        self.assertTrue(record.last_update)

    def test_refresh_null_values(self):
        record, _mock = self._refresh(
            (200, {"balance": None, "credit_limit": None}, b"{}")
        )
        self.assertEqual(record.state, "ok")
        self.assertEqual(record.balance, 0.0)
        self.assertEqual(record.credit_limit_currency, False)

    def test_refresh_http_errors(self):
        for status in (401, 500):
            record, _mock = self._refresh((status, None, b""))
            self.assertEqual(record.state, "error")
            self.assertTrue(record.last_error)

    def test_refresh_non_json(self):
        record, _mock = self._refresh((200, None, b"<html>"))
        self.assertEqual(record.state, "error")
        self.assertTrue(record.last_error)

    def test_connection_error(self):
        with patch(MIXIN + "._zipnova_request", side_effect=UserError("boom")):
            record = self.Balance._refresh_company(self.company)
        self.assertEqual(record.state, "error")
        self.assertIn("boom", record.last_error)

    def test_missing_credentials(self):
        self.company.sudo().write({"zipnova_key": False})
        with patch(MIXIN + "._zipnova_request") as mock:
            record = self.Balance._refresh_company(self.company)
        mock.assert_not_called()
        self.assertEqual(record.state, "error")
        self.assertTrue(record.last_error)

    def test_one_record_per_company_and_open_action(self):
        with patch(MIXIN + "._zipnova_request", return_value=(200, {}, b"{}")):
            action = self.Balance.action_open_balance()
            self.Balance.action_open_balance()
        records = self.Balance.search([("company_id", "=", self.company.id)])
        self.assertEqual(len(records), 1)
        self.assertEqual(action["res_id"], records.id)

    def test_web_url(self):
        action = self.Balance.action_open_zipnova_web()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "new")
