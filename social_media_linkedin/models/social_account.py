# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import itertools
import logging
import re
import time
from datetime import date, datetime, timedelta
from urllib.parse import quote, urljoin

import pytz
import requests

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.social_media_base.social_utils import (
    _generate_timestamps,
    convert_to_date,
    social_url_encode,
)

from ..social_linkedin_utils import (
    _ADS_STATUS_LEVELS_LINKEDIN,
    _FIELDS_CAMPAIGN_LINKEDIN,
    _FIELDS_STATISTIC_LINKEDIN,
    _URL_AUTH_V2_LINKEDIN,
    _URL_FEED_UPDATE_LINKEDIN,
    _URL_LINKEDIN,
    _URL_REST_LINKEDIN,
    _URL_V2_LINKEDIN,
    _URN_ORGANIZATION_LINKEDIN,
    _URN_VIDEO_LINKEDIN,
    _VIDEO_POLL_ATTEMPTS_LINKEDIN,
    _VIDEO_POLL_DELAY_LINKEDIN,
    _VIDEO_UPLOAD_PART_SIZE_LINKEDIN,
    _linkedin_error_code,
    _linkedin_error_detail,
)
from .utm_campaign import DELETED_LINKEDIN_STATUSES

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """LinkedIn implementation of the social account API calls."""

    _inherit = "social.account"

    linkedin_account_id = fields.Char(
        compute="_compute_linkedin_account_id", store=True
    )
    refresh_token_expires_in = fields.Date(string="Expire Refresh Token")
    linkedin_client_id = fields.Char(string="Client ID", groups="base.group_system")
    linkedin_secret = fields.Char(
        string="Client Secret",
        groups="base.group_system",
    )

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "linkedin",
                "https://www.linkedin.com/company/"
                f"{self.linkedin_account_id}/admin/dashboard/",
            )
        ]

    @api.depends("remote_ref", "media_type")
    def _compute_linkedin_account_id(self):
        for social_account in self:
            if social_account.media_type == "linkedin" and social_account.remote_ref:
                social_account.linkedin_account_id = social_account.remote_ref.split(
                    ":"
                )[-1]
            else:
                social_account.linkedin_account_id = False

    def unique_account(self, linkedin_client_id=None, linkedin_secret=None):
        """Reject a LinkedIn application already used by another account.

        Archived accounts are checked too, as they keep their credentials.
        """
        account_sudo = self.sudo()
        account_count = account_sudo.with_context(active_test=False).search_count(
            [
                (
                    "linkedin_client_id",
                    "=",
                    linkedin_client_id or account_sudo.linkedin_client_id,
                ),
                (
                    "linkedin_secret",
                    "=",
                    linkedin_secret or account_sudo.linkedin_secret,
                ),
            ]
        )
        if account_count > 0:
            raise UserError(
                _(
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
        """Perform a LinkedIn API request.

        :return: the parsed JSON dict when ``return_json`` is True and the
                 response status is 200; the raw ``requests.Response``
                 otherwise. Callers must check the returned type.
        """
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
        except requests.exceptions.RequestException as ex:
            raise UserError(
                _("Error connecting to LinkedIn: %(error)s", error=ex)
            ) from ex

    @api.model
    def _linkedin_error_message(self, error):
        """Build a message for the user out of what LinkedIn answered.

        The codes that name a problem the user can act on get their own
        explanation. Anything else is reported with the explanation that
        LinkedIn itself gives, instead of its raw answer.

        :param error: what LinkedIn answered, usually a ``requests.Response``.
        :rtype: str
        """
        code = _linkedin_error_code(error)
        if code == "invalid_client":
            return _(
                "LinkedIn rejected the credentials of the App. Check the "
                "Client ID and the Client Secret of your LinkedIn App."
            )
        if code in ("invalid_grant", "invalid_request"):
            return _(
                "The authorization of LinkedIn is no longer valid. Please "
                "restart the account association process."
            )
        if code == "REVOKED_ACCESS_TOKEN":
            return _(
                "The access token of LinkedIn was revoked. Update the "
                "account to authorize it again."
            )
        return _linkedin_error_detail(error)

    def update_account(self):
        res = super().update_account()
        if self.media_type == "linkedin":
            account_sudo = self.sudo()
            ctx = dict(res.get("context", {}))
            ctx.update(
                {
                    "default_linkedin_client": account_sudo.linkedin_client_id,
                    "default_linkedin_secret": account_sudo.linkedin_secret,
                }
            )
            res["context"] = ctx
        return res

    def _refresh_token(self):
        account_sudo = self.sudo()
        response = self._request_linkedin(
            method="POST",
            endpoint="/accessToken",
            token=True,
            headers=self.media_id._get_linkedin_headers(),
            params_fields=["grant_type", "refresh_token", "client_id", "client_secret"],
            params_values={
                "grant_type": "refresh_token",
                "refresh_token": account_sudo.refresh_access_token,
                "client_id": account_sudo.linkedin_client_id,
                "client_secret": account_sudo.linkedin_secret,
            },
        )
        if isinstance(response, dict):
            return response
        else:
            raise UserError(
                _(
                    "REFRESH TOKEN: %(error)s",
                    error=self._linkedin_error_message(response),
                )
            )

    def _prepare_url_upload_image(self):
        """Register the upload of an image and return its URN and upload URL.

        :rtype: tuple
        """
        image = self._request_linkedin(
            method="POST",
            endpoint="/images",
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
            params_fields=["action"],
            params_values={"action": "initializeUpload"},
            json_data={
                "initializeUploadRequest": {
                    "owner": self.remote_ref,
                }
            },
        )
        if not isinstance(image, dict):
            raise UserError(
                _(
                    "UPLOADING IMAGE: %(error)s",
                    error=self._linkedin_error_message(image),
                )
            )
        value_upload_image = image.get("value", {})
        return value_upload_image.get("image", {}), value_upload_image.get("uploadUrl")

    def _prepare_images_for_post(self, image_ids=None, image_datas=None):
        """Upload the images of a post with the Images API.

        :param image_ids: The attachments holding the images.
        :param image_datas: A single image already encoded in base64.
        :return: The URNs of the uploaded images.
        :rtype: list
        """
        images_upload = []
        if image_datas:
            image_ids = [image_datas.split(",")[-1]]
        for image in image_ids or []:
            image_urn, url_upload_image = self._prepare_url_upload_image()
            upload_image = self._request_linkedin(
                method="PUT",
                complete_url=url_upload_image,
                headers=self.media_id._get_linkedin_headers(
                    self.sudo().access_token, content_type="application/octet-stream"
                ),
                data=base64.b64decode(image if isinstance(image, str) else image.datas),
                return_json=False,
            )
            if upload_image.status_code not in (200, 201):
                raise UserError(
                    _(
                        "UPLOADING IMAGE: %(error)s",
                        error=self._linkedin_error_message(upload_image),
                    )
                )
            images_upload.append(image_urn)
        return images_upload

    def _linkedin_initialize_video_upload(self, file_size_bytes):
        """Register the upload of a video with the Videos API.

        :param file_size_bytes: The size of the video, which LinkedIn uses to
            decide in how many parts it has to be uploaded.
        :return: The URN of the video, its upload instructions and the token
            that identifies the upload.
        :rtype: tuple
        """
        video = self._request_linkedin(
            method="POST",
            endpoint="/videos",
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
            params_fields=["action"],
            params_values={"action": "initializeUpload"},
            json_data={
                "initializeUploadRequest": {
                    "owner": self.remote_ref,
                    "fileSizeBytes": file_size_bytes,
                    "uploadCaptions": False,
                    "uploadThumbnail": False,
                }
            },
        )
        if not isinstance(video, dict):
            raise UserError(
                _(
                    "UPLOADING VIDEO: %(error)s",
                    error=self._linkedin_error_message(video),
                )
            )
        value_upload_video = video.get("value", {})
        return (
            value_upload_video.get("video"),
            value_upload_video.get("uploadInstructions", []),
            value_upload_video.get("uploadToken", ""),
        )

    def _linkedin_upload_video_parts(self, video_data, upload_instructions):
        """Upload every part of a video and return the ETags of the parts.

        LinkedIn puts the video back together in the order of these ETags, so
        they are collected in the order of the upload instructions.

        :rtype: list
        """
        part_ids = []
        for instruction in upload_instructions:
            first_byte = instruction.get("firstByte", 0)
            last_byte = instruction.get(
                "lastByte", first_byte + _VIDEO_UPLOAD_PART_SIZE_LINKEDIN - 1
            )
            upload_part = self._request_linkedin(
                method="PUT",
                complete_url=instruction.get("uploadUrl"),
                headers=self.media_id._get_linkedin_headers(
                    self.sudo().access_token, content_type="application/octet-stream"
                ),
                data=video_data[first_byte : last_byte + 1],
                return_json=False,
            )
            if upload_part.status_code not in (200, 201):
                raise UserError(
                    _(
                        "UPLOADING VIDEO: %(error)s",
                        error=self._linkedin_error_message(upload_part),
                    )
                )
            part_ids.append(upload_part.headers.get("etag", "").strip('"'))
        return part_ids

    def _linkedin_finalize_video_upload(self, video_urn, upload_token, part_ids):
        """Tell LinkedIn that every part of a video has been uploaded."""
        finalize_video = self._request_linkedin(
            method="POST",
            endpoint="/videos",
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
            params_fields=["action"],
            params_values={"action": "finalizeUpload"},
            json_data={
                "finalizeUploadRequest": {
                    "video": video_urn,
                    "uploadToken": upload_token,
                    "uploadedPartIds": part_ids,
                }
            },
            return_json=False,
        )
        if finalize_video.status_code not in (200, 201):
            raise UserError(
                _(
                    "UPLOADING VIDEO: %(error)s",
                    error=self._linkedin_error_message(finalize_video),
                )
            )

    def _linkedin_video_poll_settings(self):
        """Return how often and how long a video status may be polled.

        :rtype: tuple
        """
        get_param = self.env["ir.config_parameter"].sudo().get_param
        try:
            attempts = int(
                get_param(
                    "social_media_linkedin.video_poll_attempts",
                    _VIDEO_POLL_ATTEMPTS_LINKEDIN,
                )
            )
            delay = float(
                get_param(
                    "social_media_linkedin.video_poll_delay",
                    _VIDEO_POLL_DELAY_LINKEDIN,
                )
            )
        except (TypeError, ValueError):
            return _VIDEO_POLL_ATTEMPTS_LINKEDIN, _VIDEO_POLL_DELAY_LINKEDIN
        return attempts, delay

    def _linkedin_wait_video_available(self, video_urn):
        """Wait until LinkedIn has finished processing a video.

        A video that is still being processed cannot be published, so the post
        would be rejected.

        :raise UserError: When LinkedIn fails to process the video or takes
            longer than the configured timeout.
        """
        attempts, delay = self._linkedin_video_poll_settings()
        for attempt in range(attempts):
            response = self._request_linkedin(
                endpoint=f"/videos/{quote(video_urn)}",
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                return_json=False,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "GET VIDEO STATUS: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
            video = response.json()
            status = video.get("status", "")
            if status == "AVAILABLE":
                return True
            if status == "PROCESSING_FAILED":
                raise UserError(
                    _(
                        "LinkedIn could not process the video: %(reason)s",
                        reason=video.get("processingFailureReason", status),
                    )
                )
            if attempt < attempts - 1:
                time.sleep(delay)
        raise UserError(
            _(
                "LinkedIn is still processing the video after %(seconds)s "
                "seconds. Please try to publish the post again later.",
                seconds=int(attempts * delay),
            )
        )

    def _prepare_videos_for_post(self, video_ids):
        """Upload the videos of a post with the Videos API.

        :return: The URNs of the videos, once LinkedIn has processed them.
        :rtype: list
        """
        videos_upload = []
        for video in video_ids or []:
            video_data = base64.b64decode(video.datas)
            (
                video_urn,
                upload_instructions,
                upload_token,
            ) = self._linkedin_initialize_video_upload(len(video_data))
            part_ids = self._linkedin_upload_video_parts(
                video_data, upload_instructions
            )
            self._linkedin_finalize_video_upload(video_urn, upload_token, part_ids)
            self._linkedin_wait_video_available(video_urn)
            videos_upload.append(video_urn)
        return videos_upload

    def _linkedin_create_post(self, message, image_ids=None, video_ids=None):
        """Publish a post with its media through the Posts API.

        LinkedIn does not accept images and videos in the same post, so the
        images are ignored when the post carries a video.

        :return: The URN of the published post or False when the account has
            no access token.
        :rtype: str | bool
        """
        if not self.sudo().access_token:
            return False
        video_urns = self._prepare_videos_for_post(video_ids)
        image_urns = [] if video_urns else self._prepare_images_for_post(image_ids)
        entity_post = {
            "author": f"{_URN_ORGANIZATION_LINKEDIN}{self.linkedin_account_id}",
            "commentary": message or "",
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if video_urns:
            entity_post["content"] = {"media": {"id": video_urns[0]}}
        elif len(image_urns) == 1:
            entity_post["content"] = {"media": {"id": image_urns[0]}}
        elif image_urns:
            # LinkedIn does not sponsor a multi-image post, so this content is
            # only reachable when the post has no campaign.
            entity_post["content"] = {
                "multiImage": {"images": [{"id": urn} for urn in image_urns]}
            }
        response = self._request_linkedin(
            method="POST",
            endpoint="/posts",
            headers=self.media_id._get_linkedin_headers(
                self.sudo().access_token, content_type="application/json"
            ),
            json_data=entity_post,
            return_json=False,
        )
        if response.status_code != 201:
            raise UserError(
                _(
                    "CREATING POST: %(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        return response.headers.get("x-restli-id")

    @api.model
    def _get_linkedin_oauth_wizard(self, state):
        """Return the association wizard that started this OAuth flow.

        The wizard is looked up by its state token and by its creator, so a
        state token that leaks out of the authorization URL cannot be used
        from another session to associate an account.
        """
        if not state:
            return self.env["wizard.social.account"].browse()
        return (
            self.env["wizard.social.account"]
            .sudo()
            .search(
                [
                    ("csrf_state_token", "=", state),
                    ("create_uid", "=", self.env.user.id),
                ],
                limit=1,
            )
        )

    @api.model
    def _consume_linkedin_oauth_wizard(self, state):
        """Drop the wizard of this OAuth flow so its state cannot be replayed."""
        self._get_linkedin_oauth_wizard(state).unlink()

    def get_access_token_linkedin(
        self, authorization_code, redirect_endpoint_uri, kwargs
    ):
        """Exchange the authorization code for an access token.

        :return: The client id, the client secret and the token response.
        :rtype: tuple
        """
        wizard_social_account = self._get_linkedin_oauth_wizard(kwargs.get("state", ""))
        if not wizard_social_account:
            raise UserError(
                _(
                    "Invalid OAuth state token. Please restart the "
                    "account association process."
                )
            )
        client_id = wizard_social_account.linkedin_client
        client_secret = wizard_social_account.linkedin_secret
        params = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": urljoin(self.get_base_url(), redirect_endpoint_uri),
            "client_id": client_id,
            "client_secret": client_secret,
        }
        return client_id, client_secret, self._request_linkedin(
            endpoint="/accessToken", params=params, timeout=10, token=True
        )

    def get_account_linkedin(self, access_token):
        """Read the organizations administered with this token.

        On an empty recordset every administered organization is returned;
        otherwise only the one of this account.

        :return: Dicts with ``id``, ``localizedName``, ``vanityName`` and
            ``logo``.
        :rtype: list
        """
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
                    complete_url = [
                        element
                        for element in logo_elements
                        if "logo_400_400" in element.get("artifact", "")
                    ] or [logo_elements[0]]
                    identifiers = complete_url[0].get("identifiers", [])
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
                            ("remote_ref", "=", organization_id),
                        ],
                        limit=1,
                    )
                )
                account_id.message_post(
                    body=self._linkedin_error_message(response_organizations)
                    or _("Error obtaining information from the organization"),
                )
        return organizations_data

    def create_account_linkedin(self, client_id, client_secret, token):
        """Create or update the accounts of the organizations of this token.

        An existing account is only reused when the current user is allowed
        to associate it, and it is reactivated if it was archived.
        """
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
                            ("create_uid", "=", self.env.user.id),
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
                    seconds=token.get("refresh_token_expires_in", 0),
                )
                for organization in organizations:
                    remote_ref = f"{_URN_ORGANIZATION_LINKEDIN}{organization.get('id')}"
                    social_account = self._find_account_to_associate(
                        "linkedin",
                        remote_ref,
                        username=organization.get("vanityName", False),
                    )
                    if social_account:
                        social_account._check_can_associate()
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
                        "linkedin_account_id": organization.get("id"),
                        "remote_ref": remote_ref,
                    }
                    if not social_account:
                        values_data.update(
                            {
                                "media_id": self.env.ref(
                                    "social_media_linkedin.social_media_linkedin"
                                ).id,
                            }
                        )
                        self.sudo().create(dict(values_data, user_id=self.env.user.id))
                    else:
                        if not social_account.active:
                            values_data["active"] = True
                        social_account.sudo().write(values_data)

                wizard_account_id.unlink()
                self._trigger_initial_sync()
            else:
                raise UserError(
                    _(
                        "Creating account: LinkedIn answered without an "
                        "access token. %(error)s",
                        error=self._linkedin_error_message(token),
                    )
                )
        else:
            raise UserError(
                _(
                    "Creating account: %(error)s",
                    error=self._linkedin_error_message(token),
                )
            )

    def _get_linkedin_advertising_account(self):
        """Return the advertising account URN matching the account environment.

        :return: The advertising account URN or False if none is found.
        :rtype: str | bool
        """
        advertising_account_id = self.advertising_account_id
        if not advertising_account_id:
            response = self._request_linkedin(
                endpoint="/adAccountsV2",
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                params_fields=["q", "fields"],
                params_values={"q": "search", "fields": "id,test"},
                params_values_char_ignore={"fields": [{"all": ","}]},
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code == 200:
                total = response.json().get("paging", {}).get("total", 0)
                if total > 0:
                    elements = response.json().get("elements", [])
                    filter_test = False
                    if self.enviroment == "test":
                        filter_test = True
                    filter_account = list(
                        filter(lambda x: x.get("test", False) == filter_test, elements)
                    )
                    advertising_account_id = (
                        f"urn:li:sponsoredAccount:{filter_account[0]['id']}"
                        if filter_account
                        else False
                    )
            else:
                raise UserError(
                    _(
                        "Error get advertising account in Linkedin: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
        return advertising_account_id

    def _get_linkedin_ad_account_id(self):
        """Return the identifier of the advertising account, without its URN.

        :return: The identifier or False when the account has no advertising
                 account.
        :rtype: str | bool
        """
        advertising_account = self._get_linkedin_advertising_account()
        return advertising_account.split(":")[-1] if advertising_account else False

    def _fetch_linkedin_creatives(self, campaign_urns=None):
        """Fetch the creatives of the advertising account.

        The Creatives API replaces ``adCreativesV2``: it answers the status
        set by the advertiser and accepts both share and ugcPost references,
        and it paginates with a cursor instead of an index.

        :param campaign_urns: Restrict the search to these campaign URNs.
        :return: The creative elements, filtered by the environment of the
                 account.
        :rtype: list
        """
        ad_account_id = self._get_linkedin_ad_account_id()
        if not ad_account_id:
            return []
        is_test = self.enviroment == "test"
        elements = []
        page_token = None
        while True:
            params_fields = ["q", "sortOrder", "pageSize"]
            params_values = {
                "q": "criteria",
                "sortOrder": "ASCENDING",
                "pageSize": 100,
            }
            if campaign_urns:
                params_fields.append("campaigns")
                params_values["campaigns"] = list(campaign_urns)
            if page_token:
                params_fields.append("pageToken")
                params_values["pageToken"] = page_token
            response = self._request_linkedin(
                endpoint=f"/adAccounts/{ad_account_id}/creatives",
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                params_fields=params_fields,
                params_values=params_values,
                return_json=False,
                format_quote=True,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "GET ADS: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
            data = response.json()
            page_elements = data.get("elements", [])
            elements += [
                element
                for element in page_elements
                if bool(element.get("isTest", False)) == is_test
            ]
            page_token = data.get("metadata", {}).get("nextPageToken")
            if not page_elements or not page_token:
                break
        return elements

    def _fetch_linkedin_ad_entities(self, endpoint):
        """Fetch every element of an Ads search endpoint, following pagination.

        :param endpoint: The Ads API endpoint (e.g. "/adCampaignsV2").
        :return: The list of elements.
        :rtype: list
        """
        elements = []
        start = 0
        count = 100
        while True:
            response = self._request_linkedin(
                endpoint=endpoint,
                headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
                params_fields=["q", "start", "count"],
                params_values={"q": "search", "start": start, "count": count},
                token=True,
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "Error getting campaigns from Linkedin: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
            data = response.json()
            page_elements = data.get("elements", [])
            elements += page_elements
            start += count
            if not page_elements or start >= data.get("paging", {}).get("total", 0):
                break
        return elements

    def _upsert_linkedin_campaigns(self, groups, campaigns):
        """Create or update the campaign groups and campaigns from Ads elements.

        :param groups: adCampaignGroupsV2 elements.
        :param campaigns: adCampaignsV2 elements.
        :return: The number of created groups and campaigns.
        :rtype: dict
        """
        UtmGroup = self.env["utm.group.campaign"]
        UtmCampaign = self.env["utm.campaign"]
        Currency = self.env["res.currency"]
        counts = {"groups": 0, "campaigns": 0}
        groups_by_urn = {}
        group_statuses = dict(UtmGroup._fields["linkedin_status"].selection)
        campaign_statuses = dict(UtmCampaign._fields["linkedin_status"].selection)
        campaign_formats = dict(UtmCampaign._fields["linkedin_format"].selection)
        campaign_objectives = dict(UtmCampaign._fields["linkedin_objective"].selection)
        for element in groups:
            urn = f"urn:li:sponsoredCampaignGroup:{element['id']}"
            total_budget = element.get("totalBudget", {})
            status = (element.get("status") or "").lower()
            vals = {
                "name": element.get("name", ""),
                "remote_ref": urn,
                "total_budget": float(total_budget.get("amount", 0) or 0),
                "linkedin_status": status if status in group_statuses else False,
            }
            currency = Currency.search(
                [("name", "=", total_budget.get("currencyCode"))], limit=1
            )
            if currency:
                vals["currency_id"] = currency.id
            group = UtmGroup.search([("remote_ref", "=", urn)], limit=1)
            if group:
                if group.linkedin_needs_update:
                    group.message_post(
                        body=_(
                            "Import kept the local pending changes. "
                            "LinkedIn values: name: %(name)s, "
                            "total budget: %(total_budget)s %(currency)s",
                            name=vals["name"],
                            total_budget=vals["total_budget"],
                            currency=total_budget.get("currencyCode", ""),
                        )
                    )
                    for field in ("name", "total_budget", "currency_id"):
                        vals.pop(field, None)
                was_deleted = group.linkedin_status in DELETED_LINKEDIN_STATUSES
                group.with_context(skip_linkedin_needs_update=True).write(vals)
                if (
                    not was_deleted
                    and group.linkedin_status in DELETED_LINKEDIN_STATUSES
                ):
                    group.message_post(
                        body=_(
                            "This campaign group was deleted on LinkedIn. It "
                            "is kept in Odoo as history because LinkedIn "
                            "still returns it with its performance data."
                        )
                    )
            else:
                group = UtmGroup.create(vals)
                counts["groups"] += 1
            groups_by_urn[urn] = group
        for element in campaigns:
            urn = f"urn:li:sponsoredCampaign:{element['id']}"
            group_urn = element.get("campaignGroup", "")
            group = groups_by_urn.get(group_urn) or UtmGroup.search(
                [("remote_ref", "=", group_urn)], limit=1
            )
            status = (element.get("status") or "").lower()
            vals = {
                "name": element.get("name", ""),
                "remote_ref": urn,
                "unit_cost": float(element.get("unitCost", {}).get("amount", 0) or 0),
                "daily_budget": float(
                    element.get("dailyBudget", {}).get("amount", 0) or 0
                ),
                "media_id": self.media_id.id,
                "account_id": self.id,
                "linkedin_status": status if status in campaign_statuses else False,
                "linkedin_is_test": element.get("test", False),
            }
            ad_format = element.get("format")
            if ad_format in campaign_formats:
                vals["linkedin_format"] = ad_format
            objective = element.get("objectiveType")
            if objective in campaign_objectives:
                vals["linkedin_objective"] = objective
            if group:
                vals["campaign_group_id"] = group.id
            campaign = UtmCampaign.search([("remote_ref", "=", urn)], limit=1)
            if campaign:
                if re.fullmatch(
                    rf"{re.escape(vals['name'])}( \[\d+\])?",
                    campaign.name or "",
                ):
                    vals.pop("name")
                if campaign.linkedin_needs_update:
                    campaign.message_post(
                        body=_(
                            "Import kept the local pending changes. "
                            "LinkedIn values: name: %(name)s, "
                            "unit cost: %(unit_cost)s, "
                            "daily budget: %(daily_budget)s, "
                            "campaign group: %(group)s",
                            name=element.get("name", ""),
                            unit_cost=vals["unit_cost"],
                            daily_budget=vals["daily_budget"],
                            group=group.name if group else "",
                        )
                    )
                    for field in (
                        "name",
                        "unit_cost",
                        "daily_budget",
                        "campaign_group_id",
                    ):
                        vals.pop(field, None)
                was_deleted = campaign.linkedin_status in DELETED_LINKEDIN_STATUSES
                campaign.with_context(skip_linkedin_needs_update=True).write(vals)
                if (
                    not was_deleted
                    and campaign.linkedin_status in DELETED_LINKEDIN_STATUSES
                ):
                    campaign.message_post(
                        body=_(
                            "This campaign was deleted on LinkedIn. It is "
                            "kept in Odoo as history because LinkedIn still "
                            "returns it with its performance data."
                        )
                    )
            else:
                UtmCampaign.create(vals)
                counts["campaigns"] += 1
        return counts

    def _link_linkedin_creatives(self, creatives):
        """Fill the creative URN of the posts referenced by the creatives.

        :param creatives: Creatives API elements.
        :return: The number of newly linked posts.
        :rtype: int
        """
        PostAccount = self.env["social.post.account"]
        linked = 0
        for element in creatives:
            reference = element.get("content", {}).get("reference")
            if not reference:
                continue
            post_account = PostAccount.search(
                [
                    ("remote_ref", "=", reference),
                    ("account_id", "=", self.id),
                ],
                limit=1,
            )
            creative_urn = str(element["id"])
            if post_account and post_account.creative_urn != creative_urn:
                post_account.creative_urn = creative_urn
                linked += 1
        return linked

    def action_import_campaigns(self):
        res = super().action_import_campaigns()
        if self.media_id.media_type != "linkedin":
            return res
        try:
            advertising_account_id = self._get_linkedin_advertising_account()
            if not advertising_account_id:
                return {
                    "success": False,
                    "message": _(
                        "No LinkedIn advertising account is available for "
                        "the account %(account)s.",
                        account=self.display_name,
                    ),
                    "groups": 0,
                    "campaigns": 0,
                    "ads": 0,
                }
            groups = [
                element
                for element in self._fetch_linkedin_ad_entities("/adCampaignGroupsV2")
                if element.get("account") == advertising_account_id
            ]
            campaigns = [
                element
                for element in self._fetch_linkedin_ad_entities("/adCampaignsV2")
                if element.get("account") == advertising_account_id
            ]
            campaign_urns = {
                f"urn:li:sponsoredCampaign:{element['id']}" for element in campaigns
            }
            creatives = self._fetch_linkedin_creatives(campaign_urns=campaign_urns)
        except UserError as error:
            return {
                "success": False,
                "message": str(error),
                "groups": 0,
                "campaigns": 0,
                "ads": 0,
            }
        counts = self._upsert_linkedin_campaigns(groups, campaigns)
        counts["ads"] = self._link_linkedin_creatives(creatives)
        return {
            "success": True,
            "message": _(
                "%(groups)s campaign group(s), %(campaigns)s campaign(s) "
                "and %(ads)s sponsored post(s) imported from LinkedIn.",
                **counts,
            ),
            "groups": counts["groups"],
            "campaigns": counts["campaigns"],
            "ads": counts["ads"],
        }

    def validate_linkedin_access_token(self, access_token):
        """Ask LinkedIn whether the given access token is still active.

        :rtype: bool
        """
        account_sudo = self.sudo()
        data = {
            "client_id": account_sudo.linkedin_client_id,
            "client_secret": account_sudo.linkedin_secret,
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
            today = datetime.now(tz=timezone).date()
            if (
                self.expire_access_token_date and self.expire_access_token_date < today
            ) or (
                self.refresh_token_expires_in and self.refresh_token_expires_in < today
            ):
                is_valid_token_access = self.validate_linkedin_access_token(
                    self.sudo().access_token
                    or self.env.context.get("access_token", False)
                )
                if not is_valid_token_access:
                    account_sudo = self.sudo()
                    self.env["wizard.social.account"].sudo().create(
                        {
                            "account_id": self.id,
                            "media_id": self.media_id.id,
                            "linkedin_client": account_sudo.linkedin_client_id,
                            "linkedin_secret": account_sudo.linkedin_secret,
                            "update_token": True,
                        }
                    ).with_context(**ctx)._update_account()
                elif not ctx.get("not_notify", False):
                    self._notify_user_client(
                        notif_type="social_form_success",
                        notif_message=_("The token is valid."),
                        media="linkedin",
                        account_name=self.name or "LINKEDIN",
                    )
            elif not ctx.get("not_notify", False):
                self._notify_user_client(
                    notif_type="social_form_success",
                    notif_message=_("The token is valid."),
                    media="linkedin",
                    account_name=self.name or "LINKEDIN",
                )

        return res

    def _get_posts(self, params_fields=None, params_values=None, add_values=False):
        """Fetch posts, by author without arguments or by URN with ``ids``.

        ``add_values`` merges the author query params into the given ones.

        :return: Dicts with ``id``, ``commentary``, ``content``,
            ``publishedAt``, ``createdAt`` and ``author``, whatever the query
            mode.
        """
        self.ensure_one()
        params_field_default = ["q", "author", "count"]
        params_value_default = {
            "q": "author",
            "author": f"{_URN_ORGANIZATION_LINKEDIN}{self.linkedin_account_id}",
            "count": 100,
        }
        if add_values:
            params_fields += params_field_default
            params_values.update(params_value_default)
        elif not params_fields:
            params_fields = params_field_default
            params_values = params_value_default
        is_batch_get = "ids" in params_fields
        response = self._request_linkedin(
            endpoint="/posts",
            headers=self.media_id._get_linkedin_headers(
                self.sudo().access_token,
                x_restli_method="BATCH_GET" if is_batch_get else "FINDER",
            ),
            params_fields=params_fields,
            params_values=params_values,
            return_json=False,
        )
        if response.status_code != 200:
            raise UserError(
                _(
                    "GET POSTS: %(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        response_posts = response.json()
        if is_batch_get:
            elements = response_posts.get("results", {}).values()
        else:
            elements = response_posts.get("elements", [])
        return [
            {
                "id": post["id"],
                "commentary": post.get("commentary", ""),
                "content": post.get("content", {}),
                "publishedAt": post.get("publishedAt", 0),
                "createdAt": post.get("createdAt", 0),
                "author": post.get("author", ""),
            }
            for post in elements
            if post.get("id")
        ]

    def _get_linkedin_images_download_url(self, image_urns):
        """Return the download URL of each image, resolved in a single call.

        The Posts API only answers the URN of the images of a post, so the
        Images API is asked for the URL to download them from. A failure is
        logged instead of raised: the images are a complement of the post and
        must not stop the statistics pass.

        :param image_urns: The URNs of the images to resolve.
        :return: The download URL by image URN.
        :rtype: dict
        """
        if not image_urns:
            return {}
        response = self._request_linkedin(
            endpoint="/images",
            headers=self.media_id._get_linkedin_headers(
                self.sudo().access_token, x_restli_method="BATCH_GET"
            ),
            params_fields=["ids"],
            params_values={"ids": list(image_urns)},
            return_json=False,
        )
        if response.status_code != 200:
            _logger.warning(
                "Could not read the images of LinkedIn: %s",
                self._linkedin_error_message(response),
            )
            return {}
        return {
            urn: image.get("downloadUrl")
            for urn, image in response.json().get("results", {}).items()
            if image.get("downloadUrl")
        }

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
                {"shares": [",".join([val.get("id") for val in share_posts])]}
            )
            response = self._request_linkedin(
                endpoint="/organizationalEntityShareStatistics",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.sudo().access_token, x_restli_method="FINDER"
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
                raise UserError(
                    _(
                        "GET SHARE POSTS STATISTICS: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
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
                {"ids": [",".join([val.get("id") for val in ugc_posts])]}
            )
            response = self._request_linkedin(
                endpoint="/socialActions",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.sudo().access_token
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
                raise UserError(
                    _(
                        "GET UGC POSTS STATISTICS: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
        return data

    def get_entity_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
        params_values_char_ignore=None,
        format_quote=None,
    ):
        """Merge the statistics of the share posts and of the UGC posts.

        Both endpoints are needed because each one ignores the URN type of
        the other.

        :return: Statistics tuple by post URN.
        :rtype: dict
        """
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
        params_fields = list(params_fields)
        params_values = dict(params_values)
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
            if "shares" in params_fields:
                params_fields.remove("shares")
            params_fields.remove("q")
            params_fields.remove("organizationalEntity")
            if "timeIntervals" in params_fields:
                params_fields.remove("timeIntervals")
            params_values.pop("shares", None)
            params_values.pop("q")
            params_values.pop("organizationalEntity")
            params_values.pop("timeIntervals", None)
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
                    if post_id:
                        ugc_posts = account._get_posts(
                            **{
                                "params_fields": ["ids"],
                                "params_values": {"ids": [post_id]},
                            }
                        )
                    else:
                        ugc_posts = account._get_posts()
                    if not post_id:
                        PostAccount.search(
                            [
                                (
                                    "remote_ref",
                                    "not in",
                                    list(map(lambda x: x["id"], ugc_posts)),
                                ),
                                ("remote_ref", "!=", False),
                                ("account_id", "=", account.id),
                            ]
                        ).write(
                            {
                                "post_account_url": False,
                                "remote_ref": False,
                                "state": "deleted",
                            }
                        )
                    post_reactions = account.get_entity_statistics(posts=ugc_posts)
                    post_data_reactions = {}
                    post_ids = []
                    if post_reactions:
                        post_data_reactions.update(post_reactions)
                    urns = [post["id"] for post in ugc_posts if post.get("id")]
                    post_accounts_by_urn = {}
                    for existing in PostAccount.search([("remote_ref", "in", urns)]):
                        post_accounts_by_urn.setdefault(existing.remote_ref, existing)
                    for ugc_post in ugc_posts:
                        post_account = post_accounts_by_urn.get(
                            ugc_post.get("id"), PostAccount
                        )
                        content = ugc_post.get("content", {})
                        ugc_post_urn = ugc_post.get("id")
                        post_ids.append({"id": ugc_post_urn})
                        post_data_reaction = post_data_reactions.get(ugc_post_urn, {})
                        data = {
                            "remote_ref": ugc_post_urn,
                            "post_account_url": (
                                f"{_URL_FEED_UPDATE_LINKEDIN}{ugc_post_urn}"
                            ),
                            "message": ugc_post.get("commentary", ""),
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
                                miliseconds=ugc_post.get("publishedAt")
                                or int(datetime.now(tz=pytz.UTC).timestamp() * 1000),
                                expire_date=False,
                            ),
                            "actor_urn": ugc_post.get("author", False),
                            "has_video": str(
                                content.get("media", {}).get("id", "")
                            ).startswith(_URN_VIDEO_LINKEDIN),
                            "state": "posted",
                        }
                        attach_images = post_account._get_assets_save(
                            content, account=account
                        )
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
            _logger.exception("Error updating the LinkedIn posts statistics")
            self._notify_user_client(
                notif_type="social_kanban_danger",
                notif_message=self._linkedin_error_message(ex),
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
        if not self:
            account_ids = self.search([("media_type", "=", "linkedin")])
        elif any(account.media_type == "linkedin" for account in self):
            account_ids = self
        else:
            return data
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
                posts=account.post_account_ids.mapped(lambda x: {"id": x.remote_ref}),
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
            param_values[
                "search"
            ] = f"({search_campaign},campaigns:(values:List({','.join(campaign_ids)})))"
            params_values_char_ignore = {"search": [{"1,2,3,4,5,6,7": ":"}]}
        response = self._request_linkedin(
            endpoint="/adCampaignsV2",
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
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
            raise UserError(
                _(
                    "GET CAMPAIGNS: %(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
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
            params_fields.append("creatives")
            params_values.update(
                {
                    "pivots": ["CREATIVE"],
                    "creatives": list(ads_ids),
                }
            )
        response = self._request_linkedin(
            endpoint="/adAnalyticsV2",
            headers=self.media_id._get_linkedin_headers(self.sudo().access_token),
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
            raise UserError(
                _(
                    "GET CAMPAIGNS STATISTICS: %(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        return statistics

    def _get_statistics_ads(self, ads_ids, start_date, end_date):
        return self._get_statistics(
            ads_ids=ads_ids, start_date=start_date, end_date=end_date
        )

    def _load_ads(self, start_date=None, end_date=None):
        start_date, end_date = self._get_default_filter_date(start_date, end_date)
        ads = self._fetch_linkedin_creatives()

        ads_parse = []
        if ads:
            ads_ids = list(map(lambda x: x["id"], ads))
            ads_statistics = self._get_statistics_ads(
                ads_ids, start_date=None, end_date=None
            )

            campaign_ids = list(map(lambda x: x["campaign"], ads))
            ads_campaigns = self._get_campaigns(
                start_date, end_date, campaign_ids=campaign_ids
            )

            references = {
                ad["id"]: ad.get("content", {}).get("reference", False) for ad in ads
            }
            post_ids = [reference for reference in references.values() if reference]
            ads_ugc_posts = {}
            if post_ids:
                ads_ugc_posts = {
                    ugc_post["id"]: ugc_post
                    for ugc_post in self._get_posts(
                        params_fields=["ids"], params_values={"ids": post_ids}
                    )
                }
            for ad in ads:
                statistic = list(
                    filter(
                        lambda x: ad["id"] in x["pivotValues"],
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
                ugc_post = ads_ugc_posts.get(references.get(ad["id"], False), False)
                if ugc_post:
                    post = {
                        "id": ugc_post["id"],
                        "name": ugc_post.get("commentary", ""),
                    }
                campaign_data = campaign[0] if campaign else {}
                account_id = campaign_data.get("account", "").split(":")[-1]
                ad.update(
                    {
                        "media_type": self.media_type,
                        "statistic": statistic[0] if len(statistic) > 0 else {},
                        "campaign": campaign_data,
                        "created": convert_to_date(
                            miliseconds=ad["createdAt"],
                            expire_date=False,
                            format_date="%d/%m/%Y",
                        ),
                        "status": ad.get("intendedStatus", ""),
                        "status_level": _ADS_STATUS_LEVELS_LINKEDIN.get(
                            ad.get("intendedStatus", ""), "secondary"
                        ),
                        "status_detail": ", ".join(ad.get("servingHoldReasons", [])),
                        "post": post,
                        "url": f"{_URL_LINKEDIN}{account_id}/"
                        f"creatives?creativeIds="
                        f"{quote(str([ad['id'].split(':')[-1]]))}",
                    }
                )
                ads_parse.append(ad)
        return ads_parse

    def _load_ads_accounts(self):
        res = super()._load_ads_accounts()
        ads = list(res.get("ads", []))
        account_ids = self.search([("media_type", "=", "linkedin")])
        for account in account_ids:
            ads_linkedin = account._load_ads()
            ads = list(itertools.chain(ads, ads_linkedin))
        res["ads"] = ads
        return res

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
                                    "remote_ref",
                                    "=",
                                    post_ids[0]["id"],
                                ),
                                ("remote_ref", "!=", False),
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
                                            "remote_ref",
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
        except Exception:
            _logger.exception("Error checking the LinkedIn media updates")
        return update
