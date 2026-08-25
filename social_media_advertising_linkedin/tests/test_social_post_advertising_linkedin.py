# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest.mock import MagicMock, patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import Form
from odoo.tools import mute_logger

from odoo.addons.social_media_linkedin.tests.test_common_linkedin import (
    PATCH_ACCOUNT_LINKEDIN,
)

from .test_common_advertising_linkedin import (
    PATCH_ADVERTISING_ACCOUNT_LINKEDIN,
    TestSocialCommonAdvertisingLinkedin,
)

LOGGER_POST_ACCOUNT_ADVERTISING_LINKEDIN = (
    "odoo.addons.social_media_advertising_linkedin.models.social_post_account"
)
LOGGER_POST_ACCOUNT_BASE = "odoo.addons.social_media_base.models.social_post_account"


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
            return_value=(post_account_urn, []),
        ), patch.object(
            type(self.SocialPostAccountLinkedin.account_id),
            "_get_posts",
            autospec=True,
            return_value=fake_response,
        ), patch.object(
            type(self.SocialPostAccountLinkedin),
            "_get_assets_save",
            autospec=True,
            return_value=[],
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
