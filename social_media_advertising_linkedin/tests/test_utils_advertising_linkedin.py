# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.social_media_advertising_linkedin.social_advertising_linkedin_utils import (  # noqa: E501
    _RUN_SCHEDULE_DAYS_LINKEDIN,
    run_schedule_window_linkedin,
)
from odoo.addons.social_media_linkedin.social_linkedin_utils import (
    epoch_milliseconds,
)

from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin

MILLISECONDS_PER_DAY = 24 * 3600 * 1000


class TestUtilsAdvertisingLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_run_schedule_window_linkedin(self):
        """The schedule starts now and lasts what LinkedIn proposes."""
        before = epoch_milliseconds(fields.Datetime.now())
        start, end = run_schedule_window_linkedin()
        after = epoch_milliseconds(fields.Datetime.now())
        self.assertGreaterEqual(start, before)
        self.assertLessEqual(start, after)
        self.assertEqual(
            end - start,
            _RUN_SCHEDULE_DAYS_LINKEDIN * MILLISECONDS_PER_DAY,
            msg="How long the window lasts is a decision of LinkedIn, not of "
            "the base helpers, which only convert the bounds.",
        )
