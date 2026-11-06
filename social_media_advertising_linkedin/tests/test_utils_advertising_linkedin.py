# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import tagged

from ..social_advertising_linkedin_utils import default_statistics_window
from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin


@tagged("post_install", "-at_install")
class TestDefaultStatisticsWindow(TestSocialCommonAdvertisingLinkedin):
    """``default_statistics_window`` only fills in the bounds nobody gave.

    A pure function of ``social_advertising_linkedin_utils``, tested here
    rather than through the accounts that happen to call it.
    """

    def test_default_statistics_window_keeps_both_bounds(self):
        """A window the caller bounded travels untouched."""
        start_date = datetime(2025, 1, 1)
        end_date = start_date + timedelta(days=30)
        self.assertEqual(
            default_statistics_window(start_date, end_date), (start_date, end_date)
        )

    def test_default_statistics_window_fills_both_bounds(self):
        """A caller with no dates to give asks for the last ``months``."""
        before = fields.Datetime.now()
        start, end = default_statistics_window(None, None, months=3)
        self.assertGreaterEqual(end, before)
        self.assertLess(start, before - relativedelta(months=2))
        self.assertGreater(start, before - relativedelta(months=4))

    def test_default_statistics_window_fills_only_what_is_missing(self):
        """The bound the caller gave is kept, the other one is completed."""
        end_date = datetime(2025, 2, 1)
        start, end = default_statistics_window(None, end_date)
        self.assertEqual(end, end_date)
        self.assertLess(start, fields.Datetime.now())
