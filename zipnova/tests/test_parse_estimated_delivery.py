from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestParseEstimatedDelivery(TransactionCase):
    def _parse(self, value):
        return self.env["choose.delivery.carrier"]._parse_estimated_delivery(value)

    def test_parse_estimated_delivery(self):
        zulu = self._parse("2026-11-17T23:59:00Z")
        self.assertEqual(zulu, datetime(2026, 11, 17, 23, 59))
        self.assertIsNone(zulu.tzinfo)

        utc_offset = self._parse("2026-11-17T23:59:00+00:00")
        self.assertEqual(utc_offset, datetime(2026, 11, 17, 23, 59))
        self.assertIsNone(utc_offset.tzinfo)

        argentina = self._parse("2026-11-17T23:59:00-03:00")
        self.assertEqual(argentina, datetime(2026, 11, 18, 2, 59))
        self.assertIsNone(argentina.tzinfo)

        naive = self._parse("2026-11-17T23:59:00")
        self.assertEqual(naive, datetime(2026, 11, 17, 23, 59))
        self.assertIsNone(naive.tzinfo)

        self.assertFalse(self._parse(""))
        self.assertFalse(self._parse(False))
        self.assertFalse(self._parse("not-a-date"))
