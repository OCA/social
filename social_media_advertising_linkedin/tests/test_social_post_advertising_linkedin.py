# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

import psycopg2
from psycopg2 import errorcodes

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.link_tracker.models.link_tracker import LinkTracker
from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
    PATCH_POST_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)

LOGGER_POST_ACCOUNT_ADVERTISING_LINKEDIN = (
    "odoo.addons.social_media_advertising_linkedin.models.social_post_account"
)
LOGGER_POST_ACCOUNT_BASE = "odoo.addons.social_media_base.models.social_post_account"
_URL = "https://www.binhex.cloud/"
_BASE_URL = "http://testserver"


@tagged("post_install", "-at_install")
class TestSocialPostAdvertisingLinkedin(TestSocialCommonAdvertisingLinkedin):
    def test_check_publishable_with_an_advertising_account(self):
        """The publication works against the advertising account in use."""
        post_account = self.SocialPostAccountCampaignLinkedin
        post_account.social_campaign_id.linkedin_format = "STANDARD_UPDATE"
        post_account._check_publishable()
        self.assertEqual(
            post_account.account_id._require_linkedin_ad_account_id(),
            "999",
            msg="The check has to resolve the advertising account in use.",
        )

    def test_check_publishable_without_an_advertising_account(self):
        """Nothing is resolved on the fly, so publishing an ad is refused.

        The check has to raise before the post reaches LinkedIn: the
        creative is created afterwards and its failure is only reported.
        """
        post_account = self.SocialPostAccountCampaignLinkedin
        post_account.social_campaign_id.linkedin_format = "STANDARD_UPDATE"
        self.AdvertisingAccountLinkedin.write({"is_current": False})
        with self.assertRaises(UserError) as error:
            post_account._check_publishable()
        self.assertIn("No LinkedIn advertising account is in use", str(error.exception))

    def test_get_post_errors_calls_super(self):
        """The advertising rules add to what the connector already refused."""
        post = self.SocialPostAccountCampaignLinkedin.post_id
        parent_cls = self._get_parent_class_defining(post, "_get_post_errors")
        with patch.object(
            parent_cls,
            "_get_post_errors",
            autospec=True,
            return_value=["Refused by the connector"],
        ) as mock_super:
            errors = post._get_post_errors("linkedin")
        self.assertEqual(errors[0], "Refused by the connector")
        mock_super.assert_called_once()

    def test_advertising_account_is_asked_for_the_account_alone(self):
        """The advertising account is not a limit of LinkedIn but of one account.

        Asked without an account, as the form asks, it says nothing: the post
        is publishable on any other LinkedIn account that does have one.
        """
        post_account = self.SocialPostAccountCampaignLinkedin
        post_account.social_campaign_id.linkedin_format = "STANDARD_UPDATE"
        self.AdvertisingAccountLinkedin.write({"is_current": False})
        self.assertFalse(post_account.post_id._get_post_errors("linkedin"))
        self.assertIn(
            "No LinkedIn advertising account is in use",
            "\n".join(
                post_account.post_id._get_post_errors(
                    "linkedin", account=post_account.account_id
                )
            ),
        )

    def test_get_linkedin_campaign_format_errors(self):
        """The post and its campaign must share the LinkedIn ad format."""
        post = self.SocialPostAccountCampaignLinkedin.post_id
        campaign = post.social_campaign_id
        campaign.linkedin_format = "STANDARD_UPDATE"
        self.assertFalse(post._get_linkedin_campaign_format_errors())

        post.video_ids = [Command.set([self.create_attachment("test_video.mp4").id])]
        self.assertIn(
            "'Single video' format",
            "\n".join(post._get_linkedin_campaign_format_errors()),
        )

        campaign.linkedin_format = "SINGLE_VIDEO"
        self.assertFalse(post._get_linkedin_campaign_format_errors())
        post.video_ids = [Command.clear()]
        self.assertIn(
            "only accepts posts containing a video",
            "\n".join(post._get_linkedin_campaign_format_errors()),
        )

    def test_get_linkedin_campaign_format_errors_multi_image(self):
        """LinkedIn does not sponsor a post carrying several images."""
        post = self.SocialPostAccountCampaignLinkedin.post_id
        post.social_campaign_id.linkedin_format = "STANDARD_UPDATE"
        post.image_ids = [
            Command.set(
                [
                    self.create_attachment("image_1.png").id,
                    self.create_attachment("image_2.png").id,
                ]
            )
        ]
        self.assertIn(
            "several images", "\n".join(post._get_linkedin_campaign_format_errors())
        )

        post.image_ids = [Command.set([self.create_attachment("image_1.png").id])]
        self.assertFalse(post._get_linkedin_campaign_format_errors())

    @patch(PATCH_ADVERTISING_ACCOUNT_LINKEDIN.format("_get_linkedin_ad_account_id"))
    @patch(PATCH_ACCOUNT_LINKEDIN.format("_request_linkedin"))
    def test_action_campaign_post(self, mock_request_linkedin, mock_get_ad_account_id):
        creative_urn = "urn:li:sponsoredCreative:123456"
        mock_get_ad_account_id.return_value = "999"
        campaign = self.SocialPostCampaignLinkedin.social_campaign_id
        campaign.remote_ref = "urn:li:sponsoredCampaign:001"
        mock_request_linkedin.side_effect = [
            MagicMock(status_code=201, headers={"x-restli-id": creative_urn}),
        ]
        res = self.SocialPostAccountCampaignLinkedin._action_campaign_post(
            self.SocialPostAccountCampaignLinkedin.id
        )
        self.assertEqual(res, creative_urn)
        self.assertEqual(
            mock_request_linkedin.call_args.kwargs["endpoint"],
            "/adAccounts/999/creatives",
        )

        mock_request_linkedin.side_effect = [
            MagicMock(status_code=404, headers={"x-restli-id": creative_urn}),
        ]
        with self.assertRaises(UserError):
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )

        campaign.remote_ref = False
        with self.assertRaises(UserError) as context:
            self.SocialPostAccountCampaignLinkedin._action_campaign_post(
                self.SocialPostAccountCampaignLinkedin.id
            )
        self.assertIn("has not been created on LinkedIn", str(context.exception))
        self.assertEqual(mock_request_linkedin.call_count, 2)

    def test_post_check_messages_multi_image_campaign(self):
        """The multi-image limitation is shown when the campaign is chosen."""
        error = "does not sponsor posts with several images"
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "image_ids": [
                    Command.set(
                        [
                            self.create_attachment("one.jpg").id,
                            self.create_attachment("two.jpg").id,
                        ]
                    )
                ],
            }
        )
        self.assertFalse(post.message_error)

        post.social_campaign_id = self.SocialAdvertisingCampaignLinkedin
        self.assertIn(error, post.message_error)
        self.assertIn(
            self.SocialAdvertisingCampaignLinkedin.display_name, post.message_error
        )

        post.image_ids = [Command.set([self.create_attachment("one.jpg").id])]
        self.assertFalse(post.message_error)

    def test_post_check_messages_multi_image_without_linkedin_campaign(self):
        """A campaign of another media does not create a sponsored post."""
        post = self.SocialPost.create(
            {
                "message": self.test_message,
                "account_ids": [Command.set(self.SocialAccountLinkedin.ids)],
                "social_campaign_id": self.SocialAdvertisingCampaignLinkedin2.id,
                "image_ids": [
                    Command.set(
                        [
                            self.create_attachment("one.jpg").id,
                            self.create_attachment("two.jpg").id,
                        ]
                    )
                ],
            }
        )
        self.assertFalse(post.message_error)

    def _set_linkedin_campaign(self, remote_ref=False):
        group = self.SocialAdvertisingCampaignGroup.create({"name": "Test Group"})
        campaign = self.SocialAdvertisingCampaign.create(
            {
                "name": "Test Campaign",
                "campaign_group_id": group.id,
                "media_id": self.media_linkedin_data_id.id,
                "account_ids": [Command.link(self.SocialAccountLinkedin.id)],
                "remote_ref": remote_ref,
            }
        )
        self.SocialPostLinkedin.write({"social_campaign_id": campaign.id})
        return campaign

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_action_post_campaign_precheck_blocks_publish(self):
        """A failing precheck must not reach LinkedIn.

        The guard turns the error into a failed line instead of propagating
        it, so the other accounts of the post keep their own result.
        """
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self._set_linkedin_campaign()
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
        ) as mock_linkedin_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            mock_linkedin_create_post.assert_not_called()
        self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
        self.assertIn(
            "has not been created on LinkedIn yet",
            self.SocialPostAccountLinkedin.failed_description,
        )

    @mute_logger(LOGGER_POST_ACCOUNT_BASE)
    def test_action_post_multi_image_campaign_is_not_published(self):
        """The multi-image guard must run before reaching LinkedIn."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self._set_linkedin_campaign(remote_ref="urn:li:sponsoredCampaign:100")
        self.SocialPostLinkedin.write(
            {
                "image_ids": [
                    Command.set(
                        [
                            self.create_attachment("one.jpg").id,
                            self.create_attachment("two.jpg").id,
                        ]
                    )
                ]
            }
        )
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
        ) as mock_linkedin_create_post:
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
            mock_linkedin_create_post.assert_not_called()
        self.assertEqual(self.SocialPostAccountLinkedin.state, "failed")
        self.assertIn(
            "several images", self.SocialPostAccountLinkedin.failed_description
        )

    @mute_logger(LOGGER_POST_ACCOUNT_ADVERTISING_LINKEDIN)
    def test_action_post_campaign_failure_keeps_posted(self):
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        self._set_linkedin_campaign(remote_ref="urn:li:sponsoredCampaign:100")
        post_account_urn = "urn:li:share:122809890045"
        fake_response = [
            {
                "id": post_account_urn,
                "content": {"media": {"id": "urn:li:image:1"}},
            }
        ]
        with patch.object(
            type(self.SocialPostLinkedin),
            "_filter_by_media_types",
            autospec=True,
            return_value=self.SocialPostAccountLinkedin,
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_linkedin_create_post",
            autospec=True,
            return_value=(post_account_urn, {}),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=fake_response,
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_action_campaign_post",
            autospec=True,
            side_effect=UserError("Creative error"),
        ):
            self.SocialPostAccountLinkedin._action_post(self.SocialPostLinkedin)
        self.assertEqual(self.SocialPostAccountLinkedin.state, "posted")
        self.assertEqual(
            self.SocialPostAccountLinkedin.remote_ref,
            post_account_urn,
        )
        self.assertFalse(self.SocialPostAccountLinkedin.creative_urn)

    def test_republish_keeps_the_imported_creative(self):
        """A non-sponsored publication keeps a creative linked by the import."""
        self.SocialPostAccountLinkedin.creative_urn = "urn:li:sponsoredCreative:7"
        self.assertFalse(self.SocialPostAccountLinkedin._requires_campaign_post())
        values = self.SocialPostAccountLinkedin._linkedin_published_values(
            "urn:li:share:1"
        )
        self.assertNotIn("creative_urn", values)
        self.assertEqual(
            self.SocialPostAccountLinkedin.creative_urn, "urn:li:sponsoredCreative:7"
        )

    def test_creative_urn_is_not_copied(self):
        """A creative belongs to a single ad, so a duplicate must not carry it."""
        self.SocialPostAccountLinkedin.creative_urn = "urn:li:sponsoredCreative:7"
        self.assertFalse(self.SocialPostAccountLinkedin.copy().creative_urn)

    def test_allow_social_campaign_ids_filters_unpublished(self):
        """Only the LinkedIn campaigns already created on LinkedIn are offered.

        The publication is reset because a published post no longer changes
        its campaign.
        """
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        campaign = self._set_linkedin_campaign()
        self.SocialPostLinkedin.invalidate_recordset()
        self.assertNotIn(campaign, self.SocialPostLinkedin.allow_social_campaign_ids)
        campaign.remote_ref = "urn:li:sponsoredCampaign:100"
        self.SocialPostLinkedin.invalidate_recordset()
        self.assertIn(campaign, self.SocialPostLinkedin.allow_social_campaign_ids)

    def test_allow_social_campaign_ids_filters_the_ad_format(self):
        """A campaign is only offered when its format matches the post content.

        The publication is reset because a published post no longer changes
        its campaign.
        """
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        standard = self._set_linkedin_campaign(
            remote_ref="urn:li:sponsoredCampaign:100"
        )
        video = self._set_linkedin_campaign(remote_ref="urn:li:sponsoredCampaign:101")
        video.linkedin_format = "SINGLE_VIDEO"
        self.SocialPostLinkedin.write({"social_campaign_id": standard.id})

        self.SocialPostLinkedin.invalidate_recordset()
        allowed = self.SocialPostLinkedin.allow_social_campaign_ids
        self.assertIn(standard, allowed)
        self.assertNotIn(video, allowed)

        self.SocialPostLinkedin.video_ids = [
            Command.set([self.create_attachment("test_video.mp4").id])
        ]
        allowed = self.SocialPostLinkedin.allow_social_campaign_ids
        self.assertIn(video, allowed)
        self.assertNotIn(standard, allowed)

    def test_onchange_clears_a_campaign_of_the_wrong_format(self):
        """Adding a video drops a campaign that cannot sponsor it anymore."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        standard = self._set_linkedin_campaign(
            remote_ref="urn:li:sponsoredCampaign:100"
        )
        video_attachment = self.create_attachment("test_video.mp4")
        form = Form(self.SocialPostLinkedin)
        self.assertEqual(form.social_campaign_id, standard)
        form.video_ids.add(video_attachment)
        self.assertFalse(form.social_campaign_id)

    def test_onchange_keeps_a_campaign_of_the_video_format(self):
        """A campaign already matching the new content is left alone."""
        self.SocialPostAccountLinkedin.write({"state": "ready", "remote_ref": False})
        video_campaign = self._set_linkedin_campaign(
            remote_ref="urn:li:sponsoredCampaign:101"
        )
        video_campaign.linkedin_format = "SINGLE_VIDEO"
        video_attachment = self.create_attachment("test_video.mp4")
        form = Form(self.SocialPostLinkedin)
        form.video_ids.add(video_attachment)
        self.assertEqual(form.social_campaign_id, video_campaign)

    def test_action_campaign_post_without_the_publication_reference(self):
        """Without the post on LinkedIn there is nothing to sponsor."""
        post_account = self.SocialPostAccountCampaignLinkedin
        with self.assertRaises(UserError) as error:
            post_account._action_campaign_post(False)
        self.assertIn("could not be generated for the post", str(error.exception))

    @mute_logger(LOGGER_POST_ACCOUNT_ADVERTISING_LINKEDIN)
    def test_published_values_report_a_creative_failure(self):
        """The post is already online, so the failure is told, never raised."""
        post_account = self.SocialPostAccountCampaignLinkedin
        messages = len(post_account.post_id.message_ids)
        with patch.object(
            type(post_account),
            "_action_campaign_post",
            autospec=True,
            side_effect=psycopg2.OperationalError("the connection was dropped"),
        ):
            values = post_account._linkedin_published_values("urn:li:share:1")
        self.assertNotIn("creative_urn", values)
        self.assertEqual(len(post_account.post_id.message_ids), messages + 1)

    def test_published_values_reraise_a_concurrency_error(self):
        """Concurrency errors must bubble up so the server retries."""

        class ConcurrencyError(psycopg2.OperationalError):
            pgcode = errorcodes.SERIALIZATION_FAILURE

        post_account = self.SocialPostAccountCampaignLinkedin
        with patch.object(
            type(post_account),
            "_action_campaign_post",
            autospec=True,
            side_effect=ConcurrencyError("serialization conflict"),
        ):
            with self.assertRaises(psycopg2.OperationalError):
                post_account._linkedin_published_values("urn:li:share:1")


@tagged("post_install", "-at_install")
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
