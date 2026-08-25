# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin

LOGGER_ADVERTISING_AD_LINKEDIN = (
    "odoo.addons.social_media_advertising_linkedin.models.social_advertising_ad"
)


class TestSocialAdvertisingAdLinkedin(TestSocialCommonAdvertisingLinkedin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SocialAdvertisingAd = cls.env["social.advertising.ad"]
        cls.ad_linkedin = cls.SocialAdvertisingAd.create(
            {
                "remote_ref": "urn:li:sponsoredCreative:1",
                "account_id": cls.SocialAccountLinkedin.id,
                "advertising_account_id": cls.AdvertisingAccountLinkedin.id,
                "campaign_id": cls.SocialAdvertisingCampaignLinkedin.id,
            }
        )

    def _patch_request(self, *responses):
        """Patch the LinkedIn calls with one answer per call."""
        return patch.object(
            type(self.SocialAccountLinkedin),
            "_request_linkedin",
            autospec=True,
            side_effect=list(responses),
        )

    def _set_stage(self, record, applies_to, code):
        record.stage_id = self.get_stage_linkedin(applies_to, code)

    def test_can_delete_remote_ad(self):
        """LinkedIn refuses a creative it accepts no changes on."""
        self.assertTrue(self.ad_linkedin.can_delete_remote_ad)
        for code in ("ARCHIVED", "CANCELED", "PENDING_DELETION", "REMOVED"):
            self._set_stage(self.ad_linkedin, "ad", code)
            self.assertFalse(
                self.ad_linkedin.can_delete_remote_ad,
                msg=f"A {code} creative is refused by LinkedIn",
            )
        for code in ("DRAFT", "ACTIVE", "PAUSED"):
            self._set_stage(self.ad_linkedin, "ad", code)
            self.assertTrue(self.ad_linkedin.can_delete_remote_ad)

    def test_an_ad_gone_from_linkedin_is_marked_removed(self):
        """An archived ad must not keep the status it was last fetched with."""
        self._set_stage(self.ad_linkedin, "ad", "PENDING_DELETION")
        self.ad_linkedin._register_remote_ad_gone()
        self.assertFalse(self.ad_linkedin.active)
        self.assertEqual(
            self.ad_linkedin.stage_id, self.get_stage_linkedin("ad", "REMOVED")
        )

    def test_delete_a_draft_ad_removes_it_everywhere(self):
        """A draft creative is deleted outright, so its record goes too."""
        self._set_stage(self.ad_linkedin, "ad", "DRAFT")
        deleted = self.generate_magic_mock(**{"status_code": 204})
        with self._patch_request(deleted) as mock_request:
            action = self.ad_linkedin.action_delete_remote_ad()
        self.assertFalse(self.ad_linkedin.exists())
        self.assertEqual(mock_request.call_count, 1)
        call_kwargs = mock_request.call_args.kwargs
        self.assertEqual(call_kwargs["method"], "DELETE")
        self.assertEqual(call_kwargs["headers"]["X-RestLi-Method"], "DELETE")
        self.assertIn(
            "/adAccounts/999/creatives/urn%3Ali%3AsponsoredCreative%3A1",
            call_kwargs["endpoint"],
        )
        self.assertEqual(action["params"]["type"], "success")

    def test_delete_an_ad_of_a_draft_campaign(self):
        """The campaign being a draft is enough for LinkedIn to delete."""
        self._set_stage(self.ad_linkedin, "ad", "ACTIVE")
        self._set_stage(self.SocialAdvertisingCampaignLinkedin, "campaign", "DRAFT")
        deleted = self.generate_magic_mock(**{"status_code": 204})
        with self._patch_request(deleted) as mock_request:
            self.ad_linkedin.action_delete_remote_ad()
        self.assertFalse(self.ad_linkedin.exists())
        self.assertEqual(mock_request.call_args.kwargs["method"], "DELETE")

    def test_delete_a_served_ad_requests_the_deletion(self):
        """A served ad is not deleted, LinkedIn only takes the request."""
        self._set_stage(self.ad_linkedin, "ad", "ACTIVE")
        self._set_stage(self.SocialAdvertisingCampaignLinkedin, "campaign", "ACTIVE")
        requested = self.generate_magic_mock(**{"status_code": 204})
        still_there = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {"intendedStatus": "PENDING_DELETION"},
            }
        )
        with self._patch_request(requested, still_there) as mock_request:
            action = self.ad_linkedin.action_delete_remote_ad()
        self.assertTrue(self.ad_linkedin.exists())
        self.assertTrue(self.ad_linkedin.active)
        self.assertEqual(
            self.ad_linkedin.stage_id, self.get_stage_linkedin("ad", "PENDING_DELETION")
        )
        # The deletion was never attempted: the request and the read back.
        self.assertEqual(mock_request.call_count, 2)
        call_kwargs = mock_request.call_args_list[0].kwargs
        self.assertEqual(call_kwargs["method"], "POST")
        self.assertEqual(call_kwargs["headers"]["X-RestLi-Method"], "PARTIAL_UPDATE")
        self.assertEqual(
            call_kwargs["json_data"],
            {"patch": {"$set": {"intendedStatus": "PENDING_DELETION"}}},
        )
        self.assertEqual(action["params"]["type"], "success")
        self.assertIn("pending", action["params"]["message"])

    def test_a_requested_deletion_already_done_archives_the_ad(self):
        """LinkedIn drops a creative with nothing to keep right away."""
        self._set_stage(self.ad_linkedin, "ad", "ACTIVE")
        self._set_stage(self.SocialAdvertisingCampaignLinkedin, "campaign", "ACTIVE")
        requested = self.generate_magic_mock(**{"status_code": 204})
        gone = self.generate_magic_mock(**{"status_code": 404})
        with self._patch_request(requested, gone):
            action = self.ad_linkedin.action_delete_remote_ad()
        self.assertTrue(self.ad_linkedin.exists())
        self.assertFalse(self.ad_linkedin.active)
        self.assertEqual(
            self.ad_linkedin.stage_id, self.get_stage_linkedin("ad", "REMOVED")
        )
        self.assertIn("deleted", action["params"]["message"])

    def test_the_status_answered_by_linkedin_wins(self):
        """The stage is the one LinkedIn reports, not the one requested."""
        self._set_stage(self.ad_linkedin, "ad", "ACTIVE")
        self._set_stage(self.SocialAdvertisingCampaignLinkedin, "campaign", "ACTIVE")
        requested = self.generate_magic_mock(**{"status_code": 204})
        removed = self.generate_magic_mock(
            **{"status_code": 200, "json_return_value": {"intendedStatus": "REMOVED"}}
        )
        with self._patch_request(requested, removed):
            self.ad_linkedin.action_delete_remote_ad()
        self.assertEqual(
            self.ad_linkedin.stage_id, self.get_stage_linkedin("ad", "REMOVED")
        )
        self.assertTrue(self.ad_linkedin.active)

    @mute_logger(LOGGER_ADVERTISING_AD_LINKEDIN)
    def test_a_refused_deletion_falls_back_to_the_request(self):
        """LinkedIn has the last word on what it deletes outright."""
        self._set_stage(self.ad_linkedin, "ad", "DRAFT")
        refused = self.generate_magic_mock(**{"status_code": 400})
        requested = self.generate_magic_mock(**{"status_code": 200})
        still_there = self.generate_magic_mock(
            **{
                "status_code": 200,
                "json_return_value": {"intendedStatus": "PENDING_DELETION"},
            }
        )
        with self._patch_request(refused, requested, still_there) as mock_request:
            self.ad_linkedin.action_delete_remote_ad()
        self.assertTrue(self.ad_linkedin.exists())
        self.assertEqual(
            self.ad_linkedin.stage_id, self.get_stage_linkedin("ad", "PENDING_DELETION")
        )
        self.assertEqual(mock_request.call_count, 3)

    @mute_logger(LOGGER_ADVERTISING_AD_LINKEDIN)
    def test_a_failed_request_leaves_the_ad_untouched(self):
        """Nothing is written when LinkedIn refuses both ways."""
        self._set_stage(self.ad_linkedin, "ad", "DRAFT")
        stage = self.ad_linkedin.stage_id
        refused = self.generate_magic_mock(**{"status_code": 400})
        with self._patch_request(refused, refused):
            with self.assertRaises(UserError):
                self.ad_linkedin.action_delete_remote_ad()
        self.assertTrue(self.ad_linkedin.exists())
        self.assertEqual(self.ad_linkedin.stage_id, stage)

    def test_delete_without_the_ads_scope(self):
        """A missing scope is explained instead of ending in a bare 403."""
        self.SocialAccountLinkedin.sudo().linkedin_granted_scopes = "r_ads"
        with self._patch_request() as mock_request:
            with self.assertRaises(UserError) as error:
                self.ad_linkedin.action_delete_remote_ad()
        self.assertIn("rw_ads", str(error.exception))
        mock_request.assert_not_called()

    def test_delete_uses_the_advertising_account_of_the_ad(self):
        """An ad belongs to the advertising account it was served from."""
        other_advertising_account = self.env["social.advertising.account"].create(
            {
                "account_id": self.SocialAccountLinkedin.id,
                "name": "Former LinkedIn Ads",
                "remote_ref": "urn:li:sponsoredAccount:111",
                "environment": "test",
            }
        )
        self.ad_linkedin.advertising_account_id = other_advertising_account
        self._set_stage(self.ad_linkedin, "ad", "DRAFT")
        deleted = self.generate_magic_mock(**{"status_code": 204})
        with self._patch_request(deleted) as mock_request:
            self.ad_linkedin.action_delete_remote_ad()
        self.assertIn("/adAccounts/111/", mock_request.call_args.kwargs["endpoint"])
