# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command

from odoo.addons.link_tracker.models.link_tracker import LinkTracker
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import TestSocialCommonAdvertisingLinkedin

_URL = "https://www.binhex.cloud/"
_BASE_URL = "http://testserver"


class TestSocialPostAccountLinkTrackerLinkedin(TestSocialCommonAdvertisingLinkedin):
    """The links of a publication are tracked before LinkedIn receives them."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("web.base.url", _BASE_URL)
        cls.startClassPatcher(
            patch.object(
                LinkTracker, "_get_title_from_url", side_effect=lambda url: url
            )
        )
        cls.utm_campaign_id = cls.env["utm.campaign"].create(
            {"name": "LinkedIn campaign"}
        )

    @patch(PATCH_POST_ACCOUNT_LINKEDIN.format("_linkedin_enrich_published_post"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_linkedin_create_post"))
    def test_the_message_sent_to_linkedin_carries_the_tracked_link(
        self, mock_create_post, mock_enrich
    ):
        """The conversion happens before the HTTP call, whatever the MRO.

        This is the regression test of the whole chain: it fails the day the
        links stop being shortened, or start being shortened after the post
        has already left for LinkedIn.
        """
        # The publication is enriched from the social media right after it is
        # sent, and no test makes a real request.
        mock_create_post.return_value = ("urn:li:share:1", [])
        post = self.SocialPost.create(
            {
                "message": f"Read it here {_URL}",
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "campaign_id": self.utm_campaign_id.id,
            }
        )
        post.action_create_post_account()
        mock_create_post.assert_called_once()
        sent_message = mock_create_post.call_args.kwargs["message"]
        self.assertIn(f"{_BASE_URL}/r/", sent_message)
        self.assertNotIn(_URL, sent_message)
        tracker = self.env["link.tracker"].search(
            [("social_post_account_id", "=", post.post_account_ids.id)]
        )
        self.assertEqual(len(tracker), 1)
        self.assertEqual(tracker.campaign_id, self.utm_campaign_id)
        self.assertEqual(tracker.medium_id, self.env.ref("utm.utm_medium_linkedin"))
        # The tracker is named after the publication, never after the url.
        self.assertEqual(
            tracker.title,
            f"[{self.media_linkedin_id.name}] "
            f"{self.SocialAccountLinkedin.name} - Read it here",
        )
