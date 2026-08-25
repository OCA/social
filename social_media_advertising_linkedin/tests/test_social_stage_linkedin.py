# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError

from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin


class TestSocialStageLinkedin(TestSocialCommonAdvertisingLinkedin):
    """The stages LinkedIn writes back are module data that has to be there."""

    def test_require_stage_returns_the_installed_one(self):
        self.assertEqual(
            self.SocialStage._require_linkedin_stage("campaign", "DRAFT"),
            self.get_stage_linkedin("campaign", "DRAFT"),
        )

    def test_require_stage_explains_a_missing_one(self):
        """A stage whose code was modified is not recreated by an upgrade."""
        self.get_stage_linkedin("campaign", "DRAFT").code = "RENAMED"
        with self.assertRaises(UserError) as error:
            self.SocialStage._require_linkedin_stage("campaign", "DRAFT")
        message = str(error.exception)
        self.assertIn("DRAFT", message)
        self.assertIn(
            "Campaign",
            message,
            msg="The message has to say which of the three scopes is missing.",
        )

    def test_require_stage_names_the_scope_of_the_ad(self):
        with self.assertRaises(UserError) as error:
            self.SocialStage._require_linkedin_stage("ad", "UNKNOWN")
        self.assertIn("Ad", str(error.exception))
