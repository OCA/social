# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import itertools
import logging
from datetime import date, datetime, timedelta

import pytz
import requests
from linkedin_api.clients.restli.client import RestliClient
from werkzeug.urls import url_join, url_quote

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.social_media_base.social_utils import (
    _generate_timestamps,
    convert_to_date,
    social_url_encode,
)

from ..social_linkedin_utils import (
    _FIELDS_CAMPAIGN_LINKEDIN,
    _FIELDS_STATISTIC_LINKEDIN,
    _URL_AUTH_V2_LINKEDIN,
    _URL_LINKEDIN,
    _URL_REST_LINKEDIN,
    _URL_V2_LINKEDIN,
    _URN_ORGANIZATION_LINKEDIN,
)

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    _inherit = "social.account"

    linkedin_account_id = fields.Char(
        compute="_compute_linkedin_account_id", store=True
    )
    linkedin_account_urn = fields.Char()
    refresh_token_expires_in = fields.Date(string="Expire Refresh Token")
    linkedin_client_id = fields.Char(string="Client ID")
    linkedin_secret = fields.Char(
        string="Client Secret",
    )

    @api.model
    def _get_restli_client(self):
        return RestliClient()

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "linkedin_account_urn",
                f"https://www.linkedin.com/company/{self.linkedin_account_id}/admin/dashboard/",
            )
        ]

    @api.depends("linkedin_account_urn")
    def _compute_linkedin_account_id(self):
        for social_account in self:
            if social_account.linkedin_account_urn:
                social_account.linkedin_account_id = (
                    social_account.linkedin_account_urn.split(":")[-1]
                )

    def unique_account(self, linkedin_client_id=None, linkedin_secret=None):
        account_count = self.with_context(active_test=False).search_count(
            [
                (
                    "linkedin_client_id",
                    "=",
                    linkedin_client_id or self.linkedin_client_id,
                ),
                ("linkedin_secret", "=", linkedin_secret or self.linkedin_secret),
            ]
        )
        if account_count > 0:
            raise ValidationError(
                self.env._(
                    "An account with this information "
                    "already exists; please also check "
                    "archived accounts."
                )
            )

    @api.model
    def _request_linkedin(
        self,
        method="GET",
        endpoint=None,
        params=None,
        headers=None,
        timeout=10,
        linkedin_v2=False,
        data=None,
        token=False,
        return_json=True,
        json_data=None,
        params_fields=None,
        params_values=None,
        params_values_char_ignore=None,
        complete_url=False,
        format_quote=False,
    ):
        try:
            base_url_linkedin = _URL_REST_LINKEDIN
            if linkedin_v2:
                base_url_linkedin = _URL_V2_LINKEDIN
            elif token:
                base_url_linkedin = _URL_AUTH_V2_LINKEDIN
            url = base_url_linkedin + endpoint if not complete_url else complete_url
            if params_fields:
                url += "?"
                url_params = []
                for param_field in params_fields:
                    url_params.append(
                        social_url_encode(
                            param_field,
                            params_values,
                            params_values_char_ignore,
                            format_quote,
                        )
                    )
                url += "&".join(url_params)
            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=timeout,
                headers=headers,
                data=data,
                json=json_data,
            )
            if return_json and response.status_code == 200:
                return response.json()
            return response
        except requests.ConnectionError as ex:
            raise ValidationError(str(ex)) from ex
        except requests.exceptions.ReadTimeout as ex:
            raise ValidationError(str(ex)) from ex

    def update_account(self):
        res = super().update_account()
        if self.media_type == "linkedin":
            ctx = dict(res.get("context", {}))
            ctx.update(
                {
                    "default_linkedin_client": self.linkedin_client_id,
                    "default_linkedin_secret": self.linkedin_secret,
                }
            )
            res["context"] = ctx
        return res

    def _refresh_token(self):
        response = self._request_linkedin(
            method="POST",
            endpoint="/accessToken",
            token=True,
            headers=self.media_id._get_linkedin_headers(),
            params_fields=["grant_type", "refresh_token", "client_id", "client_secret"],
            params_values={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_access_token,
                "client_id": self.linkedin_client_id,
                "client_secret": self.linkedin_secret,
            },
        )
        if isinstance(response, dict):
            return response
        else:
            raise ValidationError(self.env._("REFRESH TOKEN: %s") % response.text)

    def _prepare_url_upload_asset(self, feedshare="image"):
        try:
            json_data = {
                "registerUploadRequest": {
                    "owner": self.linkedin_account_urn,
                    "recipes": [f"urn:li:digitalmediaRecipe:feedshare-{feedshare}"],
                    "serviceRelationships": [
                        {
                            "identifier": "urn:li:userGeneratedContent",
                            "relationshipType": "OWNER",
                        }
                    ],
                }
            }
            asset = self._request_linkedin(
                method="POST",
                endpoint="/assets",
                headers=self.media_id._get_linkedin_headers(self.access_token),
                params_fields=["action"],
                params_values={"action": "registerUpload"},
                json_data=json_data,
                linkedin_v2=True,
            )
            if not isinstance(asset, dict):
                raise ValidationError(
                    self.env._("UPLOADING VIDEO: %(error_video)s")
                    % {"error_video": asset.text}
                )
            else:
                value_upload_asset = asset.get("value", {})
                return value_upload_asset.get("asset", {}), value_upload_asset.get(
                    "uploadMechanism", {}
                ).get(
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
                ).get("uploadUrl", {})
        except Exception as e:
            _logger.error(e)
            raise ValidationError(
                self.env._("UPLOADING VIDEO: %(error_video)s") % {"error_video": str(e)}
            ) from e

    def _prepare_url_upload_image(self):
        image = self._request_linkedin(
            method="POST",
            endpoint="/images",
            headers=self.media_id._get_linkedin_headers(self.access_token),
            params_fields=["action"],
            params_values={"action": "initializeUpload"},
            json_data={
                "initializeUploadRequest": {
                    "owner": self.linkedin_account_urn,
                }
            },
        )
        value_upload_image = image.get("value", {})
        return value_upload_image.get("image", {}), value_upload_image.get("uploadUrl")

    def _prepare_images_for_post(self, image_ids=None, image_datas=None):
        images_upload = []
        if image_datas:
            image_ids = [image_datas.split(",")[-1]]
        for image in image_ids or []:
            value_upload_asset, url_upload_asset = self._prepare_url_upload_asset()
            upload_image = self._request_linkedin(
                method="PUT",
                complete_url=url_upload_asset,
                headers=self.media_id._get_linkedin_headers(
                    self.access_token, content_type="application/octet-stream"
                ),
                data=base64.b64decode(image.datas)
                if not isinstance(image, str)
                else base64.b64decode(image),
                linkedin_v2=True,
                return_json=False,
            )
            if upload_image.status_code == 201:
                images_upload.append(value_upload_asset)
        return images_upload

    def _prepare_videos_for_post(self, video_ids):
        videos_upload = []
        for video in video_ids or []:
            value_upload_asset, url_upload_asset = self._prepare_url_upload_asset(
                feedshare="video"
            )

            upload_image = self._request_linkedin(
                method="PUT",
                complete_url=url_upload_asset,
                headers=self.media_id._get_linkedin_headers(
                    self.access_token, content_type="application/octet-stream"
                ),
                data=base64.b64decode(video.datas),
                linkedin_v2=True,
            )
            if upload_image.status_code == 201:
                videos_upload.append(value_upload_asset)
        return videos_upload

    def create_restclient_linkedin(self, resource_path, message, image_ids, video_ids):
        if self.access_token:
            assets_image_post = self._prepare_images_for_post(image_ids)
            assets_video_post = self._prepare_videos_for_post(video_ids)
            medias = []
            media_category = "NONE"
            if assets_image_post:
                medias = [
                    {
                        "status": "READY",
                        "media": asset_id,
                    }
                    for asset_id in assets_image_post
                ]
                media_category = "IMAGE"
            if assets_video_post:
                medias = [
                    {
                        "status": "READY",
                        "media": asset_id,
                    }
                    for asset_id in assets_video_post
                ]
                media_category = "VIDEO"

            entity_post = {
                "author": f"{_URN_ORGANIZATION_LINKEDIN}{self.linkedin_account_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": message},
                        "shareMediaCategory": media_category,
                        "media": medias,
                    }
                },
                # PUBLIC, CONNECTIONS (Private)
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }

            response = self._get_restli_client().create(
                resource_path=resource_path,
                entity=entity_post,
                access_token=self.access_token,
            )
            if response.status_code == 201 and response.entity_id:
                return response.entity_id
        return False

    def get_access_token_linkedin(
        self, authorization_code, redirect_endpoint_uri, kwargs
    ):
        wizard_social_account = (
            self.env["wizard.social.account"]
            .sudo()
            .search([("csrf_state_token", "=", kwargs.get("state", ""))])
        )
        params = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": url_join(self.get_base_url(), redirect_endpoint_uri),
        }
        client_id = None
        client_secret = None
        if wizard_social_account:
            client_id = wizard_social_account.linkedin_client
            client_secret = wizard_social_account.linkedin_secret
            params.update(
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
            )
        return (
            client_id,
            client_secret,
            self._request_linkedin(
                endpoint="/accessToken", params=params, timeout=10, token=True
            ),
        )

    def get_account_linkedin(self, access_token):
        response = self._request_linkedin(
            endpoint="/organizationAcls",
            headers=self.media_id._get_linkedin_headers(access_token),
            params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
        )
        organization_ids = (
            [
                organization["organization"].split(":")[-1]
                for organization in response.get("elements", [])
            ]
            if not self
            else [self.linkedin_account_id]
        )

        organizations_data = []
        for organization_id in organization_ids:
            response_organizations = self._request_linkedin(
                endpoint=f"/organizations/{organization_id}",
                linkedin_v2=True,
                headers=self.media_id._get_linkedin_headers(access_token),
                params={
                    "projection": "(id,name,vanityName,"
                    "logoV2(original~:playableStreams))"
                },
            )
            if isinstance(response_organizations, dict):
                logo_binary = None
                logo_elements = (
                    response_organizations.get("logoV2", {})
                    .get("original~", {})
                    .get("elements", [])
                )
                if logo_elements:
                    complete_url = list(
                        filter(
                            lambda x: "logo_400_400" in x.get("artifact", ""),
                            logo_elements,
                        )
                    )
                    if not complete_url and logo_elements:
                        complete_url = logo_elements[0]
                    identifiers = (
                        complete_url[0].get("identifiers", {}) if complete_url else []
                    )
                    if len(identifiers) > 0:
                        media_content = self._request_linkedin(
                            complete_url=identifiers[0].get("identifier", False),
                            return_json=False,
                        )
                        logo_binary = (
                            base64.b64encode(media_content.content)
                            if media_content.status_code == 200
                            else False
                        )

                localized_name = response_organizations.get("name", {}).get(
                    "localized", {}
                )
                organizations_data.append(
                    {
                        "id": response_organizations.get("id", False),
                        "localizedName": (
                            localized_name.get("es_ES")
                            or localized_name.get("en_US")
                            or list(localized_name.values())[0]
                        ),
                        "vanityName": response_organizations.get("vanityName", False),
                        "logo": logo_binary,
                    }
                )
            else:
                account_id = (
                    self.env["social.account"]
                    .sudo()
                    .search(
                        [
                            ("linkedin_account_urn", "=", organization_id),
                        ],
                        limit=1,
                    )
                )
                account_id.message_post(
                    body=response_organizations.json().get(
                        "message",
                        self.env._("Error obtaining information from the organization"),
                    ),
                )
        return organizations_data

    def create_account_linkedin(self, client_id, client_secret, token):
        if isinstance(token, dict):
            access_token = token.get("access_token", False)
            if access_token:
                wizard_account_id = (
                    self.env["wizard.social.account"]
                    .sudo()
                    .search(
                        [
                            ("linkedin_client", "=", client_id),
                            ("linkedin_secret", "=", client_secret),
                        ]
                    )
                )

                organizations = (
                    self.get_account_linkedin(access_token)
                    if not wizard_account_id
                    else wizard_account_id.account_id.get_account_linkedin(access_token)
                )
                expire_token = date.today() + timedelta(
                    days=token.get("expires_in", 0) / 86400
                )
                expire_refresh_token = convert_to_date(
                    seconds=token.get(
                        "refresh_token_expires_in",
                        int(datetime.now().timestamp() * 1000),
                    )
                    / 86400,
                )
                for organization in organizations:
                    social_account = self.sudo().search(
                        [
                            ("username", "=", organization.get("vanityName", False)),
                            ("media_type", "=", "linkedin"),
                        ]
                    )
                    values_data = {
                        "name": organization.get("localizedName", False),
                        "username": organization.get("vanityName", False),
                        "image_1920": organization.get("logo", False),
                        "linkedin_client_id": client_id,
                        "linkedin_secret": client_secret,
                        "access_token": access_token,
                        "refresh_access_token": token.get("refresh_token", False),
                        "expire_access_token_date": expire_token,
                        "refresh_token_expires_in": expire_refresh_token,
                    }
                    if not social_account:
                        linkedin_account_urn = (
                            f"{_URN_ORGANIZATION_LINKEDIN}{organization.get('id')}"
                        )
                        values_data.update(
                            {
                                "linkedin_account_id": organization.get("id"),
                                "linkedin_account_urn": linkedin_account_urn,
                                "media_id": self.env.ref(
                                    "social_media_linkedin.social_media_linkedin"
                                ).id,
                            }
                        )
                        self.create(values_data)
                    else:
                        social_account.write(values_data)

                wizard_account_id.unlink()

        else:
            message_error = f"Creating account: {token.text}"
            raise ValidationError(message_error)

    def validate_linkedin_access_token(self, access_token):
        data = {
            "client_id": self.linkedin_client_id,
            "client_secret": self.linkedin_secret,
            "token": access_token,
        }
        response = self._request_linkedin(
            method="POST",
            endpoint="/introspectToken",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            token=True,
        )
        if response and response.get("active", False):
            return True
        return False

    def validate_access_token(self):
        res = super().validate_access_token()
        if self.media_id.media_type == "linkedin":
            timezone = pytz.timezone(self.env.user.tz or "UTC")
            ctx = dict(self.env.context)
            if (
                self.expire_access_token_date < datetime.now(tz=timezone).date()
                or self.refresh_token_expires_in < datetime.now(tz=timezone).date()
            ):
                is_valid_token_access = self.validate_linkedin_access_token(
                    self.access_token or self.env.context("access_token", False)
                )
                if not is_valid_token_access:
                    self.env["wizard.social.account"].sudo().create(
                        {
                            "account_id": self.id,
                            "media_id": self.media_id.id,
                            "linkedin_client": self.linkedin_client_id,
                            "linkedin_secret": self.linkedin_secret,
                            "update_token": True,
                        }
                    ).with_context(**ctx)._update_account()
                elif not ctx.get("not_notify", False):
                    # Notifying the user
                    self._notify_user_client(
                        notif_type="social_form_success"
                        if is_valid_token_access
                        else "social_form_danger",
                        notif_message=self.env._("The token is %(token_valid)s valid.")
                        % {"token_valid": "not " if not is_valid_token_access else ""},
                        media="linkedin",
                        account_name=self.name or "LINKEDIN",
                    )
            elif not ctx.get("not_notify", False):
                self._notify_user_client(
                    notif_type="social_form_success",
                    notif_message=self.env._("The token is valid."),
                    media="linkedin",
                    account_name=self.name or "LINKEDIN",
                )

        return res

    def _get_posts(self, params_fields=None, params_values=None, add_values=False):
        self.ensure_one()
        params_field_default = ["q", "authors"]
        params_value_default = {
            "q": "authors",
            "authors": [f"{_URN_ORGANIZATION_LINKEDIN}{self.linkedin_account_id}"],
        }
        if add_values:
            params_fields += params_field_default
            params_values.update(params_value_default)
        else:
            params_fields = params_field_default
            params_values = params_value_default

        response = self._request_linkedin(
            endpoint="/ugcPosts",
            headers=self.media_id._get_linkedin_headers(self.access_token),
            params_fields=params_fields,
            params_values=params_values,
            linkedin_v2=True,
            return_json=False,
        )
        if response.status_code == 200:
            response_ugc_posts = response.json()
            if "ids" in params_fields:
                ugc_posts = response_ugc_posts.get("results", [])
            else:
                ugc_posts = [
                    {
                        "id": post["id"],
                        "share_content": post.get("specificContent", {}).get(
                            "com.linkedin.ugc.ShareContent", {}
                        ),
                        "firstPublishedAt": post.get("firstPublishedAt", {}),
                    }
                    for post in response_ugc_posts.get("elements", [])
                ]
        else:
            raise ValidationError(f"GET UGC POSTS: {response.json()}")
        return ugc_posts

    def get_share_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
        params_values_char_ignore=None,
        format_quote=None,
    ):
        data = {}
        if not posts:
            return data
        share_posts = list(
            filter(
                lambda x: x.get("id", False) is not False
                and "urn:li:share:" in x.get("id", ""),
                posts,
            )
        )
        if share_posts:
            params_fields.append("shares")
            params_values.update(
                {
                    "shares": [
                        "{}".format(
                            ",".join(list(map(lambda val: val.get("id"), share_posts)))
                        )
                    ]
                }
            )
            response = self._request_linkedin(
                endpoint="/organizationalEntityShareStatistics",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.access_token, x_restli_method="FINDER"
                ),
                params_fields=params_fields,
                params_values=params_values,
                params_values_char_ignore=params_values_char_ignore,
                linkedin_v2=True,
                return_json=False,
                format_quote=format_quote,
            )
            if response.status_code == 200:
                post_reactions = response.json().get("elements", [])
                data = {
                    post_reaction["share"]: (
                        post_reaction.get("totalShareStatistics", {}).get(
                            "clickCount", 0
                        ),
                        post_reaction.get("totalShareStatistics", {}).get(
                            "likeCount", 0
                        ),
                        post_reaction.get("totalShareStatistics", {}).get(
                            "commentCount", 0
                        ),
                        post_reaction.get("totalShareStatistics", {}).get(
                            "shareCount", 0
                        ),
                        post_reaction.get("totalShareStatistics", {}).get(
                            "engagement", 0
                        ),
                        post_reaction.get("totalShareStatistics", {}).get(
                            "impressionCount", 0
                        ),
                    )
                    for post_reaction in post_reactions
                }

            else:
                raise ValidationError(f"GET SHARE POSTS STATISTICS: {response.json()}")
        return data

    def get_ugc_posts_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
        params_values_char_ignore=None,
        format_quote=None,
    ):
        data = {}
        if not posts:
            return data
        ugc_posts = list(
            filter(
                lambda x: x.get("id", False) is not False
                and "urn:li:ugcPost:" in x.get("id", ""),
                posts,
            )
        )
        if ugc_posts:
            params_fields.append("ids")
            params_values.update(
                {
                    "ids": [
                        "{}".format(
                            ",".join(list(map(lambda val: val.get("id"), ugc_posts)))
                        )
                    ]
                }
            )
            response = self._request_linkedin(
                endpoint="/socialActions",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.access_token
                ),
                params_fields=params_fields,
                params_values=params_values,
                params_values_char_ignore=params_values_char_ignore,
                return_json=False,
                linkedin_v2=True,
                format_quote=format_quote,
            )
            if response.status_code == 200:
                post_reactions = response.json().get("results", [])
                data = {
                    urn_id: (
                        0,
                        post_reaction.get("likesSummary", {}).get("totalLikes", 0),
                        post_reaction.get("commentsSummary", {}).get(
                            "aggregatedTotalComments", 0
                        ),
                        0,
                        0,
                        0,
                    )
                    for urn_id, post_reaction in post_reactions.items()
                }
            else:
                raise ValidationError(f"GET UGC POSTS STATISTICS: {response.json()}")
        return data

    def get_entity_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
        params_values_char_ignore=None,
        format_quote=None,
    ):
        if not self.media_type == "linkedin":
            return {}
        if not params_fields:
            params_fields = ["q", "organizationalEntity"]
        if not params_values:
            params_values = {
                "q": "organizationalEntity",
                "organizationalEntity": f"{_URN_ORGANIZATION_LINKEDIN}"
                f"{self.linkedin_account_id}",
            }
        data = {}
        data_share = {}
        if posts:
            data_share = self.get_share_statistics(
                posts=posts,
                params_fields=params_fields,
                params_values=params_values,
                params_values_char_ignore=params_values_char_ignore,
                format_quote=format_quote,
            )
            params_fields.remove("shares")
            params_fields.remove("q")
            params_fields.remove("organizationalEntity")
            if "timeIntervals" in params_fields:
                params_fields.remove("timeIntervals")
            params_values.pop("shares")
            params_values.pop("q")
            params_values.pop("organizationalEntity")
            if "timeIntervals" in params_fields:
                params_values.remove("timeIntervals")
            data = self.get_ugc_posts_statistics(
                posts=posts,
                params_fields=params_fields,
                params_values=params_values,
                params_values_char_ignore=params_values_char_ignore,
                format_quote=format_quote,
            )
        return data | data_share

    def _update_posts_statistics(self, post_id, domain):
        statistics = super()._update_posts_statistics(post_id, domain)
        PostAccount = self.env["social.post.account"]
        if not self:
            account_ids = self.search([("media_type", "=", "linkedin")])
        elif any(val.media_type == "linkedin" for val in self):
            account_ids = self
        else:
            return statistics
        try:
            for account in account_ids:
                account.with_context(not_notify=True).validate_access_token()
                post_accounts = []
                if account.linkedin_account_id:
                    # POSTS
                    if post_id:
                        ugc_posts = account._get_posts(
                            **{
                                "params_fields": ["ids"],
                                "params_values": {"ids": [post_id]},
                            }
                        )
                    else:
                        ugc_posts = account._get_posts()
                    PostAccount.search(
                        [
                            (
                                "linkedin_post_account_urn",
                                "not in",
                                list(map(lambda x: x["id"], ugc_posts)),
                            ),
                            ("linkedin_post_account_urn", "!=", False),
                            ("account_id", "=", account.id),
                        ]
                    ).write(
                        {"post_account_url": False, "linkedin_post_account_urn": False}
                    )
                    # POSTS REACTIONS
                    post_reactions = account.get_entity_statistics(posts=ugc_posts)
                    post_data_reactions = {}
                    post_ids = []
                    if post_reactions:
                        post_data_reactions.update(post_reactions)
                    for ugc_post in ugc_posts:
                        post_account = PostAccount.search(
                            [
                                ("linkedin_post_account_urn", "=", ugc_post.get("id")),
                            ],
                            limit=1,
                        )
                        share_content = ugc_post.get("share_content", {})
                        post_id = ugc_post.get("id")
                        post_ids.append({"id": post_id})
                        post_data_reaction = post_data_reactions.get(post_id, {})
                        data = {
                            "linkedin_post_account_urn": post_id,
                            "post_account_url": f"https://www.linkedin.com/feed/update/{post_id}",
                            "message": share_content.get("shareCommentary", {}).get(
                                "text", ""
                            ),
                            "account_id": account.id,
                            "click_count": post_data_reaction[0]
                            if post_data_reaction
                            else 0,
                            "like_count": post_data_reaction[1]
                            if post_data_reaction
                            else 0,
                            "comment_count": post_data_reaction[2]
                            if post_data_reaction
                            else 0,
                            "share_count": post_data_reaction[3]
                            if post_data_reaction
                            else 0,
                            "engagement": post_data_reaction[4]
                            if post_data_reaction
                            else 0,
                            "impression_count": post_data_reaction[5]
                            if post_data_reaction
                            else 0,
                            "published_date": convert_to_date(
                                miliseconds=ugc_post.get(
                                    "firstPublishedAt",
                                    int(datetime.now().timestamp() * 1000),
                                ),
                                expire_date=False,
                            ),
                            "actor_urn": ugc_post.get("created", {}).get(
                                "actor", False
                            ),
                            "state": "posted",
                        }
                        attach_images = post_account._get_assets_save(share_content)
                        if attach_images:
                            data.update({"image_ids": attach_images})
                        if not post_account:
                            post_accounts.append(Command.create(data))
                        else:
                            post_accounts.append(Command.update(post_account.id, data))
                    update_account_data = {
                        "post_account_ids": post_accounts,
                        "need_update": False,
                    }
                    if len(post_reactions) > 0:
                        update_account_data.update(
                            account._filter_statistics(post_reactions)
                        )
                    account.write(update_account_data)
        except Exception as ex:
            self._notify_user_client(
                notif_type="social_kanban_danger",
                notif_message=str(ex),
                media="linkedin",
                account_name=self.name,
            )
        return self._get_account_statistics(statistics=statistics)

    def _get_account_statistics(self, statistics=None):
        data = self.search_read(
            [("media_type", "=", "linkedin")],
            [
                "name",
                "company_id",
                "media_id",
                "account_url",
                "impression_count",
                "interactions_count",
                "engagement",
                "need_update",
            ],
        )
        if statistics:
            data = list(
                itertools.chain(
                    statistics,
                    data,
                )
            )
        return data

    def _get_chart_account_statistics(
        self, start_date=None, end_date=None, granularity="WEEK"
    ):
        data = super()._get_chart_account_statistics(start_date, end_date, granularity)
        account_ids = self or self.search([("media_type", "=", "linkedin")])
        data_linkedin = []
        for account in account_ids:
            start_date_time, end_date_time = account._get_default_filter_date(
                start_date, end_date, time_date=True
            )
            start_date, end_date = account._get_default_filter_date(
                start_date, end_date
            )

            params_fields = ["q", "organizationalEntity", "timeIntervals", "count"]
            params_values = {
                "q": "organizationalEntity",
                "organizationalEntity": f"{_URN_ORGANIZATION_LINKEDIN}"
                f"{account.linkedin_account_id}",
                "timeIntervals": f"(timeRange:(start:{start_date_time},"
                f"end:{end_date_time})"
                f",timeGranularityType:{granularity})",
                "count": 100,
            }
            params_values_char_ignore = {"timeIntervals": [{"all": ":"}]}
            account_statistics = account.get_entity_statistics(
                posts=account.post_account_ids.mapped(
                    lambda x: {"id": x.linkedin_post_account_urn}
                ),
                params_fields=params_fields,
                params_values=params_values,
                params_values_char_ignore=params_values_char_ignore,
                format_quote=True,
            )
            freq = "W-MON"
            if granularity == "DAY":
                freq = "D"
            elif granularity == "MONTH":
                freq = "ME"
            if account_statistics:
                data_linkedin += account._map_chart_statistics(
                    account_statistics,
                    **{"freq": freq, "start_date": start_date, "end_date": end_date},
                )
        return list(itertools.chain(data, data_linkedin))

    def _get_campaigns(self, start_date=None, end_date=None, campaign_ids=None):
        start_time, end_time = _generate_timestamps(start_date, end_date)
        param_values = {
            "q": "search",
            "search": f"(startDate:(values:{start_time}),"
            f"endDate:(values:{end_time}),test:true)",
            "fields": _FIELDS_CAMPAIGN_LINKEDIN,
            "count": 100,
        }
        params_values_char_ignore = {"search": [{"all": ":"}]}
        if campaign_ids:
            search_campaign = param_values["search"].strip("()")
            param_values["search"] = (
                f"({search_campaign},campaigns:(values:List({','.join(campaign_ids)})))"
            )
            params_values_char_ignore = {"search": [{"1,2,3,4,5,6,7": ":"}]}
        response = self._request_linkedin(
            endpoint="/adCampaignsV2",
            headers=self.media_id._get_linkedin_headers(self.access_token),
            params_fields=["q", "search", "fields", "count"],
            params_values=param_values,
            params_values_char_ignore=params_values_char_ignore,
            return_json=False,
            linkedin_v2=True,
            format_quote=True,
        )

        if response.status_code == 200:
            campaigns = response.json().get("elements", [])
        else:
            raise ValidationError(f"GET CAMPAIGNS: {response.json()}")
        return campaigns

    def _get_statistics(self, ads_ids=None, start_date=None, end_date=None):
        start_date, end_date = self._get_default_filter_date(start_date, end_date)
        start_date = (
            start_date.strftime(DEFAULT_SERVER_DATE_FORMAT).split("-")
            if not isinstance(start_date, str)
            else start_date
        )
        parse_start_date = (
            f"(year:{start_date[0]},month:{int(start_date[1])},"
            f"day:{int(start_date[2])})"
        )
        end_date = (
            end_date.strftime(DEFAULT_SERVER_DATE_FORMAT).split("-")
            if not isinstance(end_date, str)
            else end_date
        )
        parse_end_date = (
            f"(year:{end_date[0]},month:{int(end_date[1])},day:{int(end_date[2])})"
        )
        date_statistics_range = f"(start:{parse_start_date},end:{parse_end_date})"

        params_fields = [
            "q",
            "pivots",
            "timeGranularity",
            "dateRange",
            "fields",
            "count",
        ]
        params_values = {
            "q": "statistics",
            "pivots": ["CAMPAIGN"],
            "timeGranularity": "ALL",
            "dateRange": date_statistics_range,
            "fields": _FIELDS_STATISTIC_LINKEDIN,
            "count": 100,
        }
        if ads_ids:
            params_fields.append("accounts")
            params_values.update(
                {
                    "pivots": ["CREATIVE"],
                    "accounts": list(
                        map(lambda x: f"urn:li:sponsoredAccount:{x}", ads_ids)
                    ),
                }
            )
        response = self._request_linkedin(
            endpoint="/adAnalyticsV2",
            headers=self.media_id._get_linkedin_headers(self.access_token),
            params_fields=params_fields,
            params_values=params_values,
            params_values_char_ignore={"dateRange": [{"all": ":"}]},
            return_json=False,
            linkedin_v2=True,
            format_quote=True,
        )

        if response.status_code == 200:
            statistics = response.json().get("elements", [])
        else:
            raise ValidationError(f"GET CAMPAIGNS STATISTICS: {response.json()}")
        return statistics

    def _get_statistics_ads(self, ads_ids, start_date, end_date):
        return self._get_statistics(
            ads_ids=ads_ids, start_date=start_date, end_date=end_date
        )

    def _load_ads(self, start_date=None, end_date=None):
        start_date, end_date = self._get_default_filter_date(start_date, end_date)
        response = self._request_linkedin(
            endpoint="/adCreativesV2",
            headers=self.media_id._get_linkedin_headers(self.access_token),
            params_fields=["q", "search", "fields", "count"],
            params_values={
                "q": "search",
                "search": "(test:false)",
                "fields": "id,reference,test,campaign,"
                "changeAuditStamps,servingStatuses",
                "count": 100,
            },
            params_values_char_ignore={"search": [{"1,2,6": ":"}]},
            return_json=False,
            linkedin_v2=True,
            format_quote=True,
        )
        if response.status_code == 200:
            ads = response.json().get("elements", [])
        else:
            raise ValidationError(f"GET ADS: {response.json()}")

        # STATISTICS
        ads_parse = []
        if ads:
            ads_ids = list(map(lambda x: x["id"], ads))
            ads_statistics = self._get_statistics_ads(
                ads_ids, start_date=None, end_date=None
            )

            # CAMPAIGNS
            campaign_ids = list(map(lambda x: x["campaign"], ads))
            ads_campaigns = self._get_campaigns(
                start_date, end_date, campaign_ids=campaign_ids
            )

            # POSTS
            post_ids = list(
                map(
                    lambda x: x["reference"],
                    list(filter(lambda x: x.get("reference", False), ads)),
                )
            )
            ads_ugc_posts = self._get_posts(
                **{"params_fields": ["ids"], "params_values": {"ids": post_ids}}
            )
            for ad in ads:
                statistic = list(
                    filter(
                        lambda x: f"urn:li:sponsoredAccount:{ad['id']}"
                        in x["pivotValues"],
                        ads_statistics,
                    )
                )
                campaign = list(
                    filter(
                        lambda x: int(ad["campaign"].split(":")[-1]) == x["id"],
                        ads_campaigns,
                    )
                )
                post = {}
                if ad.get("reference", False) and ads_ugc_posts.get(
                    ad["reference"], False
                ):
                    post = {
                        "id": ads_ugc_posts[ad["reference"]]["id"],
                        "name": ads_ugc_posts[ad["reference"]]
                        .get("specificContent", {})
                        .get("com.linkedin.ugc.ShareContent", {})
                        .get("shareCommentary", {})
                        .get("text", ""),
                    }
                account_id = campaign[0]["account"].split(":")[-1]
                ad.update(
                    {
                        "media_type": self.media_type,
                        "statistic": statistic[0] if len(statistic) > 0 else {},
                        "campaign": campaign[0] if len(campaign) > 0 else {},
                        "created": convert_to_date(
                            miliseconds=ad["changeAuditStamps"]["created"]["time"],
                            expire_date=False,
                            format_date="%d/%m/%Y",
                        ),
                        "status": ", ".join(ad["servingStatuses"]),
                        "post": post,
                        "url": f"{_URL_LINKEDIN}{account_id}/"
                        f"creatives?creativeIds={url_quote([ad['id']])}",
                    }
                )
                ads_parse.append(ad)
        return ads_parse

    def _load_ads_accounts(self):
        ads = super()._load_ads_accounts()
        account_ids = self.search([("media_type", "=", "linkedin")])
        for account in account_ids:
            ads_linkedin = account._load_ads()
            ads = list(itertools.chain(ads, ads_linkedin))
        return {
            "ads": ads,
        }

    def _run_check_media_updates(self):
        update = super()._run_check_media_updates()
        try:
            if not update:
                account_ids = self.search([("media_type", "=", "linkedin")])
                PostAccount = self.env["social.post.account"]
                for account in account_ids:
                    post_ids = account._get_posts(
                        params_fields=["sortBy"],
                        params_values={"sortBy": "LAST_MODIFIED"},
                        add_values=True,
                    )
                    if post_ids:
                        count_post = PostAccount.search_count(
                            [
                                (
                                    "linkedin_post_account_urn",
                                    "=",
                                    post_ids[0]["id"],
                                ),
                                ("linkedin_post_account_urn", "!=", False),
                                ("account_id", "=", account.id),
                            ],
                            limit=1,
                        )
                        if count_post == 0:
                            account.need_update = True
                            return self._need_update()
                        else:
                            post_reactions = account.get_entity_statistics(
                                posts=post_ids
                            )
                            for post, statistic in post_reactions.items():
                                post_account = PostAccount.search_count(
                                    [
                                        "&",
                                        (
                                            "linkedin_post_account_urn",
                                            "=",
                                            post,
                                        ),
                                        "|",
                                        (
                                            "click_count",
                                            "!=",
                                            statistic[0],
                                        ),
                                        "|",
                                        (
                                            "like_count",
                                            "!=",
                                            statistic[1],
                                        ),
                                        "|",
                                        (
                                            "comment_count",
                                            "!=",
                                            statistic[2],
                                        ),
                                        (
                                            "share_count",
                                            "!=",
                                            statistic[3],
                                        ),
                                    ]
                                )
                                if post_account:
                                    account.need_update = True
                                    return self._need_update()
        except Exception as ex:
            _logger.error(self.env._("ERROR NEDD UPDATE %(error)s", error=str(ex)))
        return update
