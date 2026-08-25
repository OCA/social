# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.social_media_linkedin.social_linkedin_utils import _SCOPE_LINKEDIN

from ..social_advertising_linkedin_utils import _SCOPE_ADS_LINKEDIN
from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin


class TestSocialMediaAdvertisingLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_get_linkedin_scopes_adds_the_ads_ones(self):
        """The authorization must ask for the Ads scopes on top of the base ones."""
        scopes = self.media_linkedin_data_id._get_linkedin_scopes()
        self.assertTrue(set(_SCOPE_LINKEDIN).issubset(scopes))
        self.assertTrue(set(_SCOPE_ADS_LINKEDIN).issubset(scopes))
        self.assertEqual(
            len(scopes),
            len(set(scopes)),
            msg="A scope requested twice is refused by LinkedIn.",
        )
