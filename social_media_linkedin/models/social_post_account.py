# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
from urllib.parse import quote

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.social_utils import convert_date_in_time

from ..social_linkedin_utils import _URL_FEED_UPDATE_LINKEDIN, _URN_IMAGE_LINKEDIN

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Publication, comments and statistics of a post on a LinkedIn account."""

    _inherit = "social.post.account"

    creative_urn = fields.Char()

    def _get_assets_save(self, content, account=None):
        """Download the images of a post that are not stored yet.

        :param content: The ``content`` of the post answered by the Posts API.
        :param account: The account to ask LinkedIn with, needed when the post
            does not exist in Odoo yet.
        :return: The commands creating the missing attachments.
        :rtype: list
        """
        media_id = str(content.get("media", {}).get("id", ""))
        image_urns = [media_id] if media_id.startswith(_URN_IMAGE_LINKEDIN) else []
        image_urns += [
            str(image.get("id", ""))
            for image in content.get("multiImage", {}).get("images", [])
            if str(image.get("id", "")).startswith(_URN_IMAGE_LINKEDIN)
        ]
        medias_exist = self._get_medias_account(image_urns)
        image_urns = [urn for urn in image_urns if urn not in medias_exist]
        if not image_urns:
            return []
        account = account or self.account_id
        download_urls = account._get_linkedin_images_download_url(image_urns)
        return [
            self._map_medias_account(**{"name": urn, "url": download_urls[urn]})
            for urn in image_urns
            if download_urls.get(urn)
        ]

    def _linkedin_advertising_accounts(self):
        return self.account_id._get_linkedin_advertising_account()

    def _action_campaign_group(self):
        advertising_account_id = self._linkedin_advertising_accounts()
        if not advertising_account_id:
            return False
        return self.post_id.campaign_id._linkedin_publish_campaign_group(
            self.account_id, advertising_account_id
        )

    def _action_campaign(self):
        campaign_group_linkedin_urn = self._action_campaign_group()
        campaign = False
        if campaign_group_linkedin_urn:
            campaign_id = self.post_id.campaign_id
            campaign = campaign_id._linkedin_verify_campaign(self.account_id)
            if not campaign:
                campaign = campaign_id._linkedin_create_campaign(
                    self.account_id,
                    self._linkedin_advertising_accounts(),
                    campaign_group_linkedin_urn,
                )
        return campaign

    def _requires_campaign_post(self):
        """Return whether publishing must create a LinkedIn sponsored creative.

        :rtype: bool
        """
        self.ensure_one()
        return bool(
            self.media_id.media_type == "linkedin"
            and self.post_id.campaign_id
            and self.post_id.campaign_id.campaign_group_id
            and self.post_id.campaign_id.media_id.media_type == "linkedin"
        )

    def _check_linkedin_campaign_format(self):
        """Check that the post matches the ad format of its campaign.

        LinkedIn only accepts creatives of the format chosen when the campaign
        was created, so publishing a video in a standard campaign would leave
        the post online without its ad. A post carrying several images is
        published as a multi-image post, which LinkedIn does not sponsor at
        all.

        :raise UserError: When the post and the campaign formats differ.
        """
        self.ensure_one()
        campaign = self.post_id.campaign_id
        has_video = bool(self.post_id.video_ids)
        is_video_campaign = campaign.linkedin_format == "SINGLE_VIDEO"
        if not has_video and len(self.post_id.image_ids) > 1:
            raise UserError(
                _(
                    "LinkedIn does not sponsor posts with several images, so "
                    "this post cannot be linked to the campaign %(campaign)s. "
                    "Publish it with a single image or without a campaign.",
                    campaign=campaign.display_name,
                )
            )
        if has_video and not is_video_campaign:
            raise UserError(
                _(
                    "The post contains a video, so it needs a campaign of the "
                    "'Single video' format. The campaign %(campaign)s uses the "
                    "'Standard update' format and LinkedIn does not allow "
                    "changing it once the campaign is created.",
                    campaign=campaign.display_name,
                )
            )
        if is_video_campaign and not has_video:
            raise UserError(
                _(
                    "The campaign %(campaign)s uses the 'Single video' format, "
                    "so it only accepts posts containing a video.",
                    campaign=campaign.display_name,
                )
            )

    def _action_campaign_post(self, post_id):
        res = super()._action_campaign_post(post_id)
        if self._requires_campaign_post():
            campaign_linkedin_urn = self.post_id.campaign_id.remote_ref
            if not campaign_linkedin_urn:
                raise UserError(
                    _(
                        "The campaign %(campaign)s has not been created on "
                        "LinkedIn yet. Use the 'Create in LinkedIn' button "
                        "on the campaign before posting.",
                        campaign=self.post_id.campaign_id.display_name,
                    )
                )
            if campaign_linkedin_urn and post_id:
                ad_account_id = self.account_id._get_linkedin_ad_account_id()
                if not ad_account_id:
                    raise UserError(
                        _(
                            "No LinkedIn advertising account is available for "
                            "the account %(account)s.",
                            account=self.account_id.display_name,
                        )
                    )
                # The Creatives API replaces ``adCreativesV2``, whose sponsored
                # status update creatives only accept activity references, so
                # the posts holding an image or a video could not be sponsored.
                response = self.account_id._request_linkedin(
                    method="POST",
                    endpoint=f"/adAccounts/{ad_account_id}/creatives",
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.sudo().access_token
                    ),
                    json_data={
                        "campaign": campaign_linkedin_urn,
                        "intendedStatus": "ACTIVE",
                        "content": {"reference": post_id},
                    },
                    return_json=False,
                )
                if response.status_code == 201:
                    res = response.headers.get("x-restli-id")
                else:
                    raise UserError(
                        _(
                            "Error creating campaign post in Linkedin: %(error)s",
                            error=self.account_id._linkedin_error_message(response),
                        )
                    )
            else:
                raise UserError(
                    _(
                        "The campaign could not be generated for the post, "
                        "please try again later."
                    )
                )
        return res

    def _action_post(self, post_id):
        res = super()._action_post(post_id)
        if any(account.media_type == "linkedin" for account in post_id.account_ids):
            post_accounts = post_id.filter_by_media_types(["linkedin"])
            for post_account in post_accounts:
                if post_account._requires_campaign_post():
                    if not post_account.post_id.campaign_id.remote_ref:
                        raise UserError(
                            _(
                                "The campaign %(campaign)s has not been "
                                "created on LinkedIn yet. Use the 'Create in "
                                "LinkedIn' button on the campaign before "
                                "posting.",
                                campaign=post_account.post_id.campaign_id.display_name,
                            )
                        )
                    post_account._check_linkedin_campaign_format()
                    post_account._linkedin_advertising_accounts()
                post_entity = post_account.account_id._linkedin_create_post(
                    message=post_account.message,
                    image_ids=post_account.post_id.image_ids,
                    video_ids=post_account.post_id.video_ids,
                )
                if post_entity:
                    ugc_post = post_account.account_id._get_posts(
                        **{
                            "params_fields": ["ids"],
                            "params_values": {"ids": [post_entity]},
                        }
                    )
                    attach_images = None
                    if ugc_post and ugc_post[0].get("content", False):
                        attach_images = post_account._get_assets_save(
                            ugc_post[0].get("content", {})
                        )
                    creative_urn = False
                    try:
                        creative_urn = post_account._action_campaign_post(post_entity)
                    except UserError:
                        _logger.exception(
                            "Error creating the LinkedIn campaign creative "
                            "for post %s",
                            post_entity,
                        )
                        post_account.post_id.message_post(
                            body=_(
                                "The post was published on LinkedIn but the "
                                "campaign creative could not be created. "
                                "Check the Ads permissions of the account."
                            )
                        )
                    post_account.write(
                        {
                            "remote_ref": post_entity,
                            "post_account_url": (
                                f"{_URL_FEED_UPDATE_LINKEDIN}{post_entity}"
                            ),
                            "creative_urn": creative_urn,
                            "image_ids": attach_images,
                            "has_video": bool(post_account.post_id.video_ids),
                            "state": "posted",
                            "published_date": fields.Datetime.now(),
                        }
                    )
                else:
                    post_account.write(
                        {
                            "state": "failed",
                        }
                    )
        return res

    def action_like_post(self, author_urn=None):
        res = super().action_like_post(author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint="/reactions",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token, content_type="application/json"
                ),
                token=True,
                return_json=False,
                linkedin_v2=True,
                params_fields=["actor"],
                params_values={"actor": author_urn},
                json_data={
                    "root": self.remote_ref,
                    "reactionType": "LIKE",
                },
            )
            message_like = ""
            if response.status_code == 201:
                like_ok = True
            elif response.status_code == 409:
                message_like = _("You have already reacted to this post.")
            elif response.status_code == 404:
                message_like = _("The post does not exist or has been deleted.")
            else:
                message_like = self.account_id._linkedin_error_message(response)
            return {"success": like_ok, "message": message_like}
        return res

    def action_like_comment(self, comment_id=None, author_urn=None):
        super().action_like_comment(author_urn)
        return {"success": False, "message": ""}

    def get_comments(self):
        data = super().get_comments()
        comments = []
        if "linkedin" == self.account_id.media_type and self.remote_ref:
            response = self.account_id._request_linkedin(
                method="GET",
                endpoint=f"/socialActions/{quote(self.remote_ref)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code == 200:
                response_comments = response.json().get("elements", [])
                comments = [
                    {
                        "id": comment.get("id"),
                        "text": comment.get("message", {}).get("text"),
                        "actor": comment.get("lastModified", {}).get("actor", {}),
                        "published_time": convert_date_in_time(
                            miliseconds=comment.get("lastModified", 0).get("time", 0),
                            timezone=self.env.user.tz,
                        ),
                        "images_url": [
                            val.get("url", {}) for val in comment.get("content", {})
                        ],
                    }
                    for comment in response_comments
                ]
            else:
                return_message = _(
                    "ERROR GET COMMENTS LINKEDIN: %(error)s",
                    error=self.account_id._linkedin_error_message(response),
                )
                _logger.error(return_message)
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
            "data": list(itertools.chain(data.get("data", []), comments)),
        }

    def create_linkedin_comment(self, post_data):
        if "linkedin" == self.account_id.media_type:
            json_data = {
                "actor": self.account_id.remote_ref,
                "message": {"text": post_data.get("body", "")},
                "object": self.remote_ref,
            }
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint=f"/socialActions/{quote(self.remote_ref)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                json_data=json_data,
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 201:
                return_message = _(
                    "ERROR CREATE COMMENT LINKEDIN: %(error)s",
                    error=self.account_id._linkedin_error_message(response),
                )
                _logger.error(return_message)
                return {
                    "success": False,
                    "message": return_message,
                }
        return {
            "success": True,
        }

    def create_comment(self, post_data, context=None):
        if "linkedin" == self.account_id.media_type:
            return self.create_linkedin_comment(post_data)
        else:
            return super().create_comment(post_data, context)

    def delete_linkedin_comment(self, comment_id, actor_urn):
        if "linkedin" == self.account_id.media_type:
            response = self.account_id._request_linkedin(
                method="DELETE",
                endpoint=f"/socialActions/{quote(self.remote_ref)}/comments/{quote(comment_id)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                params_fields=["actor"],
                params_values={"actor": actor_urn},
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 204:
                return {
                    "success": False,
                    "message": _(
                        "An error occurred while deleting the comment or it "
                        "no longer exists, please try again later."
                    ),
                }
        return {
            "success": True,
        }

    def get_linkedin_comment(self):
        if "linkedin" == self.account_id.media_type and self.remote_ref:
            response = self.account_id._request_linkedin(
                endpoint=f"/posts/{quote(self.remote_ref)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                return_json=False,
            )
            if response.status_code != 200:
                self.remote_ref = None
                self.post_account_url = None
                return False
            return True
        return False

    def _delete_post_account(self):
        if self.media_id.media_type == "linkedin" and self.remote_ref:
            delete_post = self.account_id._request_linkedin(
                method="DELETE",
                endpoint=f"/posts/{quote(self.remote_ref)}",
                headers=self.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                return_json=False,
            )
            if delete_post.status_code != 204:
                error_message = self.account_id._linkedin_error_message(
                    delete_post
                ) or _("The post could not be deleted, please try again later.")
                raise UserError(
                    _("Error deleting LinkedIn post: %(error)s", error=error_message)
                )
        return super()._delete_post_account()
