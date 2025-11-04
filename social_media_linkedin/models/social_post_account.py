# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import itertools
import logging
from urllib.parse import quote

from odoo import Command, _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.social_media_base.social_utils import (
    _generate_timestamps,
    convert_date_in_time,
)

from ..social_linkedin_utils import _URL_V2_LINKEDIN

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    _inherit = "social.post.account"

    linkedin_post_account_urn = fields.Char()
    linkedin_account_urn = fields.Char(related="account_id.linkedin_account_urn")
    creative_urn = fields.Char()

    def _get_assets_save(self, share_content):
        medias = share_content.get("media", [])
        media_ids = [val.get("media", "") for val in medias]
        medias_exist = (
            self.env["ir.attachment"]
            .search(
                [
                    ("name", "in", media_ids),
                ]
            )
            .mapped("name")
        )
        attachments = []
        for media in medias:
            if media.get("media", False) not in medias_exist and media.get(
                "originalUrl", False
            ):
                media_content = self.account_id._request_linkedin(
                    complete_url=media.get("originalUrl", False),
                    return_json=False,
                )
                if media_content.status_code == 200:
                    attachments.append(
                        Command.create(
                            {
                                "name": media.get("media", False),
                                "type": "binary",
                                "res_model": self._name,
                                "res_id": self.id,
                                "datas": base64.b64encode(media_content.content),
                            }
                        )
                    )
        return attachments

    def _linkedin_advertising_accounts(self):
        advertising_account_id = self.account_id.advertising_account_id
        if not advertising_account_id:
            response = self.account_id._request_linkedin(
                endpoint="/adAccountsV2",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token
                ),
                params_fields=["q", "fields"],
                params_values={"q": "search", "fields": "id,test"},
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code == 200:
                total = response.json().get("paging", {}).get("total", 0)
                if total > 0:
                    elements = response.json().get("elements", [])
                    filter_test = False
                    if self.account_id.environment == "test":
                        filter_test = True
                    filter_account = list(
                        filter(lambda x: x.get("test", False) == filter_test, elements)
                    )
                    advertising_account_id = (
                        "urn:li:sponsoredAccount:{}".format(filter_account[0]["id"])
                        if filter_account
                        else False
                    )
            else:
                raise ValidationError(
                    _(f"Error get advertising account in Linkedin: {response.json()}")
                )
        return advertising_account_id

    def _action_campaign_group(self):
        advertising_account_id = self._linkedin_advertising_accounts()
        group_campaign = False
        if advertising_account_id:
            post_campaign_id = self.post_id.campaign_id
            if post_campaign_id.campaign_group_id.linkedin_urn:
                group_campaign = self.account_id._request_linkedin(
                    endpoint="/adCampaignGroupsV2/{}".format(
                        post_campaign_id.campaign_group_id.linkedin_urn.split(":")[-1]
                    ),
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    token=True,
                    return_json=False,
                    linkedin_v2=True,
                )
            if group_campaign and group_campaign.status_code == 200:
                return post_campaign_id.campaign_group_id.linkedin_urn
            elif not group_campaign or group_campaign.status_code == 404:
                start, end = _generate_timestamps()
                response = self.account_id._request_linkedin(
                    method="POST",
                    endpoint="/adCampaignGroupsV2",
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    json_data={
                        "account": advertising_account_id,
                        "name": post_campaign_id.campaign_group_id.name,
                        "runSchedule": {
                            "start": start,
                            "end": end,
                        },
                        "status": "ACTIVE",
                        "totalBudget": {
                            "amount": (
                                f"{post_campaign_id.campaign_group_id.total_budget}"
                            ),
                            "currencyCode": post_campaign_id.currency_id.name,
                        },
                    },
                    token=True,
                    return_json=False,
                    linkedin_v2=True,
                )
                if response.status_code == 201:
                    group_campaign = "urn:li:sponsoredCampaignGroup:{}".format(
                        response.headers.get("Location").split("/")[-1]
                    )
                    post_campaign_id.campaign_group_id.linkedin_urn = group_campaign
                else:
                    raise ValidationError(
                        _(
                            f"Error creating group campaign "
                            f"in Linkedin: {response.json()}"
                        )
                    )
            else:
                raise ValidationError(
                    _(
                        f"Error creating group campaign "
                        f"in Linkedin: {group_campaign.json()}"
                    )
                )
        return group_campaign

    def _action_campaign(self):
        campaign_group_linkedin_urn = self._action_campaign_group()
        campaign = False
        if campaign_group_linkedin_urn:
            post_campaign_id = self.post_id.campaign_id
            if post_campaign_id.linkedin_urn:
                campaign = self.account_id._request_linkedin(
                    endpoint="/adCampaignsV2/{}".format(
                        post_campaign_id.linkedin_urn.split(":")[-1]
                    ),
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    return_json=False,
                    linkedin_v2=True,
                )
            if campaign and campaign.status_code == 200:
                return post_campaign_id.linkedin_urn
            elif not campaign or campaign.status_code == 404:
                start, end = _generate_timestamps()
                response = self.account_id._request_linkedin(
                    method="POST",
                    endpoint="/adCampaignsV2",
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    json_data={
                        "account": self._linkedin_advertising_accounts(),
                        "campaignGroup": campaign_group_linkedin_urn,
                        "name": f"{post_campaign_id.name}",
                        "type": "SPONSORED_UPDATES",
                        "offsiteDeliveryEnabled": False,
                        "runSchedule": {
                            "start": start,
                            "end": end,
                        },
                        "locale": {
                            "country": self.env.user.country_id.code or "US",
                            "language": self.env.user.lang.split("_")[0],
                        },
                        "unitCost": {
                            "amount": f"{post_campaign_id.unit_cost}",
                            "currencyCode": post_campaign_id.currency_id.name,
                        },
                        "dailyBudget": {
                            "amount": f"{post_campaign_id.daily_budget}",
                            "currencyCode": post_campaign_id.currency_id.name,
                        },
                        "status": "ACTIVE",
                    },
                    token=True,
                    return_json=False,
                    linkedin_v2=True,
                )
                if response.status_code == 201:
                    campaign = "urn:li:sponsoredCampaign:{}".format(
                        response.headers.get("Location").split("/")[-1]
                    )
                    post_campaign_id.linkedin_urn = campaign
                else:
                    raise ValidationError(
                        _(f"Error creating campaign in Linkedin: {response.json()}")
                    )
            else:
                raise ValidationError(
                    _(
                        f"""Error creating group campaign in Linkedin:
                        {campaign.json()}"""
                    )
                )

        return campaign

    def _action_campaign_post(self, post_id):
        res = super()._action_campaign_post(post_id)
        if (
            self.media_id.media_type == "linkedin"
            and self.post_id.campaign_id
            and self.post_id.campaign_id.campaign_group_id
            and self.post_id.campaign_id.media_id.media_type == "linkedin"
        ):
            campaign_linkedin_urn = self._action_campaign()
            if campaign_linkedin_urn and post_id:
                response = self.account_id._request_linkedin(
                    method="POST",
                    endpoint="/adCreativesV2",
                    headers=self.account_id.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    json_data={
                        "campaign": campaign_linkedin_urn,
                        "reference": post_id,
                        "status": "ACTIVE",
                        "type": "SPONSORED_STATUS_UPDATE",
                        "variables": {
                            "data": {
                                "com.linkedin.ads.SponsoredUpdateCreativeVariables": {}
                            }
                        },
                    },
                    token=True,
                    return_json=False,
                    linkedin_v2=True,
                )
                if response.status_code == 201:
                    res = response.headers.get("Location").split("/")[-1]
                else:
                    raise ValidationError(
                        _(
                            f"""Error creating campaign post in Linkedin:
                            {response.json()}"""
                        )
                    )
            else:
                raise ValidationError(
                    _(
                        """The campaign could not be generated for the post,
                        please try again later."""
                    )
                )
        return res

    def _action_post(self):
        res = super()._action_post()
        if any(
            account.media_type == "linkedin" for account in self.post_id.account_ids
        ):
            post_accounts = self.filter_by_media_types(["linkedin"])
            failed_post_account = self.env["social.post.account"]
            for post_account in post_accounts:
                post_entity = post_account.account_id.create_restclient_linkedin(
                    "/ugcPosts",
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
                    if ugc_post and ugc_post[0].get("share_content", False):
                        attach_images = post_account._get_assets_save(
                            ugc_post[0].get("share_content", {})
                        )
                    post_account.write(
                        {
                            "linkedin_post_account_urn": post_entity,
                            "post_account_url": f"https://www.linkedin.com/feed/update/urn:li:share:{post_entity}",
                            "published_date": fields.Datetime.now(),
                            "creative_urn": post_account._action_campaign_post(
                                post_entity
                            ),
                            "image_ids": attach_images,
                            "state": "posted",
                        }
                    )
                else:
                    failed_post_account |= post_account
        return res

    def action_like_post(self, author_urn=None):
        res = super().action_like_post(author_urn)
        if self.media_id.media_type == "linkedin":
            like_ok = False
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint="/reactions",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token, content_type="application/json"
                ),
                token=True,
                return_json=False,
                linkedin_v2=True,
                params_fields=["actor"],
                params_values={"actor": author_urn},
                json_data={
                    "root": self.linkedin_post_account_urn,
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
                message_like = response.json().get("message", "")
            return {"success": like_ok, "message": message_like}
        return res

    def action_like_comment(self, comment_id=None, author_urn=None):
        super().action_like_comment(author_urn)
        return {"success": False, "message": ""}

    def get_comments(self):
        data = super().get_comments()
        comments = []
        if "linkedin" == self.account_id.media_type and self.linkedin_post_account_urn:
            response = self.account_id._request_linkedin(
                method="GET",
                endpoint=f"/socialActions/{quote(self.linkedin_post_account_urn)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token
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
                return_message = f"Error GET COMMENTS LINKEDIN: {response.json()}"
                _logger.error(return_message)
                if not self.user_has_groups("base.group_no_one"):
                    return_message = _(
                        "An error occurred while retrieving comments, "
                        "please try again later."
                    )
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
                "actor": self.account_id.linkedin_account_urn,
                "message": {"text": post_data.get("body", "")},
                "object": self.linkedin_post_account_urn,
            }
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint=f"/socialActions/{quote(self.linkedin_post_account_urn)}/comments",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token
                ),
                json_data=json_data,
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 201:
                return_message = response.json().get("message", "")

                if not self.env.user.has_group("base.group_no_one"):
                    return_message = _(
                        "An error occurred while commenting, please try again later."
                    )
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
                endpoint=f"/socialActions/{quote(self.linkedin_post_account_urn)}/comments/{quote(comment_id)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token
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
                        """
                        An error occurred while deleting the comment or
                        it no longer exists, please try again later.
                        """
                    ),
                }
        return {
            "success": True,
        }

    def get_linkedin_comment(self):
        if "linkedin" == self.account_id.media_type and self.linkedin_post_account_urn:
            response = self.account_id._request_linkedin(
                endpoint=f"/shares/{quote(self.linkedin_post_account_urn)}",
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.access_token
                ),
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 200:
                self.linkedin_post_account_urn = None
                self.post_account_url = None
                return False
            return True
        return False

    def _delete_post_account(self):
        res = super()._delete_post_account()
        if self.media_id.media_type == "linkedin":
            if self.linkedin_post_account_urn:
                pos_account_urn = quote(self.linkedin_post_account_urn, safe="")
                delete_post = self.account_id._request_linkedin(
                    method="DELETE",
                    complete_url=f"{_URL_V2_LINKEDIN}/shares/{pos_account_urn}",
                    headers=self.media_id._get_linkedin_headers(
                        self.account_id.access_token
                    ),
                    linkedin_v2=True,
                    return_json=False,
                )
                if delete_post.status_code != 200:
                    error_message = delete_post.json().get(
                        "message",
                        _("The post could not be deleted, please try again later."),
                    )
                    raise ValidationError(error_message)
        return res

    def _action_like_linkedin_comment(self, actor_urn):
        if actor_urn:
            pass
        return {"success": False}
