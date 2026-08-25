# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import itertools
import json
import logging
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from urllib.parse import quote, urljoin

import psycopg2
import pytz
import requests
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import is_list_of

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_linkedin_utils import (
    _BATCH_GET_MAX_IDS_LINKEDIN,
    _FINDER_PARAMS_LINKEDIN,
    _POSTS_MAX_PAGES_LINKEDIN,
    _POSTS_PAGE_SIZE_LINKEDIN,
    _STATISTICS_HISTORY_MONTHS_LINKEDIN,
    _TOKEN_MARGIN_DAYS_LINKEDIN,
    _UPDATE_CHECK_DAYS_LINKEDIN,
    _UPDATE_CHECK_FIGURES_LINKEDIN,
    _URL_AUTH_V2_LINKEDIN,
    _URL_FEED_UPDATE_LINKEDIN,
    _URL_REST_LINKEDIN,
    _URL_V2_LINKEDIN,
    _URN_ORGANIZATION_LINKEDIN,
    _URN_SHARE_LINKEDIN,
    _URN_UGC_POST_LINKEDIN,
    _URN_VIDEO_LINKEDIN,
    _VIDEO_POLL_ATTEMPTS_LINKEDIN,
    _VIDEO_POLL_DELAY_LINKEDIN,
    _VIDEO_UPLOAD_PART_SIZE_LINKEDIN,
    _batch_urns_by_url_size,
    _linkedin_error_code,
    _linkedin_error_detail,
    _linkedin_is_credentials_error,
    epoch_milliseconds,
    social_url_encode,
)

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
    linkedin_statistics_checkpoint = fields.Char(
        copy=False,
        help="Technical field: the daily figures LinkedIn reported for the "
        "whole page over the last days, as of the last time the publications "
        "were imported. The check for updates compares the page against it "
        "instead of reading the statistics of every publication.",
    )
    linkedin_granted_scopes = fields.Char(
        string="Granted Scopes",
        groups="base.group_system",
        help="Scopes LinkedIn granted to the token of this account, comma "
        "separated. The next authorization asks for the scopes the installed "
        "modules need plus the ones listed here, so a scope of a product "
        "enabled on the LinkedIn application afterwards can be added by "
        "hand. The change takes effect only once the account is authorized "
        "again with Update account and Update keys, since refreshing the "
        "token alone keeps the scopes the current token was granted. A scope "
        "that the products of the application do not grant makes LinkedIn "
        "refuse the whole authorization.",
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

    def _unique_account(self, linkedin_client_id=None, linkedin_secret=None):
        """Reject a LinkedIn application already used by another account.

        Archived accounts are checked too, as they keep their credentials.
        The accounts of ``self`` are excluded, so updating the keys of an
        account is not rejected by its own credentials. On the empty recordset
        of the association flow nothing is excluded.
        """
        account_sudo = self.sudo()
        account_count = account_sudo.with_context(active_test=False).search_count(
            [
                ("id", "not in", account_sudo.ids),
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
        complete_url=False,
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
                    url_params.append(social_url_encode(param_field, params_values))
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

    @api.model
    def _linkedin_raise_error(self, prefix, response):
        """Raise what LinkedIn answered, telling the credentials errors apart.

        A refused authorization is the only failure that a new token can fix,
        so it is raised as a ``SocialCredentialsError`` and the publication
        can try again. Everything else stays a plain ``UserError``.

        :param prefix: what was being done, shown before the reason.
        :param response: what LinkedIn answered.
        """
        message = _(
            "%(prefix)s: %(error)s",
            prefix=prefix,
            error=self._linkedin_error_message(response),
        )
        if _linkedin_is_credentials_error(response):
            raise SocialCredentialsError(message)
        raise UserError(message)

    def action_update_account(self):
        """Open the update wizard, proposing the Client ID when allowed.

        ``linkedin_client_id`` is restricted to ``base.group_system``, and the
        context of an action is serialized to the browser, so the value is
        only proposed to the users that may read the field. The others simply
        type it again in the wizard, where it is editable and required.
        """
        res = super().action_update_account()
        if self.media_type == "linkedin" and self.env.user.has_group(
            "base.group_system"
        ):
            ctx = dict(res.get("context", {}))
            ctx.update(
                {
                    "default_linkedin_client": self.sudo().linkedin_client_id,
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
        if isinstance(response, dict) and response.get("access_token"):
            return response
        self._linkedin_raise_error(
            _("The LinkedIn token could not be refreshed"), response
        )

    def _linkedin_store_refreshed_token(self):
        """Ask LinkedIn for a new token and store it on the account.

        Shared by the update wizard and by the retry of a publication that
        LinkedIn refused, so both keep the same expiry dates.
        """
        self.ensure_one()
        token = self._refresh_token()
        values = {
            "access_token": token.get("access_token", False),
            "refresh_access_token": token.get("refresh_token", False),
            "expire_access_token_date": date.today()
            + timedelta(days=token.get("expires_in", 0) / 86400),
            "refresh_token_expires_in": date.today()
            + timedelta(days=token.get("refresh_token_expires_in", 0) / 86400),
        }
        scopes = self._linkedin_normalize_scopes(token.get("scope"))
        if scopes:
            values["linkedin_granted_scopes"] = scopes
        self.sudo().write(values)
        return token

    def _refresh_credentials(self):
        """Renew the access token of this LinkedIn account.

        Only the access token is renewed here: once the refresh token is gone
        the account has to be authorized again from the browser, which is not
        something a publication or a cron can do.
        """
        res = super()._refresh_credentials()
        if self.media_type != "linkedin":
            return res
        account_sudo = self.sudo()
        if not account_sudo.refresh_access_token or (
            self.refresh_token_expires_in
            and self.refresh_token_expires_in < date.today()
        ):
            return False
        try:
            self._linkedin_store_refreshed_token()
        except UserError:
            _logger.exception(
                "Could not renew the LinkedIn token of the account %s", self.id
            )
            return False
        return True

    def _linkedin_prepare_url_upload_image(self):
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
            self._linkedin_raise_error(
                _("The image could not be uploaded to LinkedIn"), image
            )
        value_upload_image = image.get("value", {})
        return value_upload_image.get("image", {}), value_upload_image.get("uploadUrl")

    def _linkedin_prepare_images_for_post(self, image_ids=None):
        """Upload the images of a post with the Images API.

        :param image_ids: The attachments holding the images.
        :return: The URNs of the uploaded images, in the same order as
            ``image_ids``. Callers rely on that order to match every
            attachment with the media it became on LinkedIn.
        :rtype: list
        """
        images_upload = []
        for image in image_ids or []:
            image_urn, url_upload_image = self._linkedin_prepare_url_upload_image()
            if not image_urn:
                raise UserError(
                    _("LinkedIn did not return the reference of the " "uploaded image.")
                )
            upload_image = self._request_linkedin(
                method="PUT",
                complete_url=url_upload_image,
                headers=self.media_id._get_linkedin_headers(
                    self.sudo().access_token, content_type="application/octet-stream"
                ),
                data=base64.b64decode(image.datas),
                return_json=False,
            )
            if upload_image.status_code not in (200, 201):
                self._linkedin_raise_error(
                    _("The image could not be uploaded to LinkedIn"), upload_image
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
            self._linkedin_raise_error(
                _("The video could not be uploaded to LinkedIn"), video
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
        for number, instruction in enumerate(upload_instructions, start=1):
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
                self._linkedin_raise_error(
                    _("The video could not be uploaded to LinkedIn"), upload_part
                )
            etag = upload_part.headers.get("etag", "").strip('"')
            if not etag:
                raise UserError(
                    _(
                        "LinkedIn did not return the identifier of the part "
                        "%(part)s of %(total)s, so the upload of the video "
                        "cannot be finalized.",
                        part=number,
                        total=len(upload_instructions),
                    )
                )
            part_ids.append(etag)
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
            self._linkedin_raise_error(
                _("The video could not be uploaded to LinkedIn"), finalize_video
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
                self._linkedin_raise_error(
                    _("The status of the video could not be read"), response
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

    def _linkedin_prepare_videos_for_post(self, video_ids):
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

        :return: The URN of the published post, or False when the account has
            no access token, together with the URNs of the images actually
            attached to it. The image URNs let the caller name the local copy
            of every attachment after the media it became on LinkedIn.
        :rtype: tuple
        """
        if not self.sudo().access_token:
            return False, []
        video_urns = self._linkedin_prepare_videos_for_post(video_ids)
        image_urns = (
            [] if video_urns else self._linkedin_prepare_images_for_post(image_ids)
        )
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
            self._linkedin_raise_error(
                _("The post could not be published on LinkedIn"), response
            )
        return response.headers.get("x-restli-id"), image_urns

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

    def _get_access_token_linkedin(
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

    def _get_linkedin_organization_logo(self, organization):
        """Download the logo of an organization, in the largest size answered.

        The projection asks for every playable stream of the logo, so the
        square of 400 pixels is preferred and any other is taken rather than
        leaving the account without a picture.

        :param organization: the organization as the Organizations API
            answered it.
        :return: the logo encoded in base64, or ``None`` when LinkedIn
            reported none and ``False`` when it could not be downloaded.
        """
        logo_elements = (
            organization.get("logoV2", {}).get("original~", {}).get("elements", [])
        )
        if not logo_elements:
            return None
        preferred = [
            element
            for element in logo_elements
            if "logo_400_400" in element.get("artifact", "")
        ] or [logo_elements[0]]
        identifiers = preferred[0].get("identifiers", [])
        if not identifiers:
            return None
        media_content = self._request_linkedin(
            complete_url=identifiers[0].get("identifier", False),
            return_json=False,
        )
        if media_content.status_code != 200:
            return False
        return base64.b64encode(media_content.content)

    def _get_account_linkedin(self, access_token):
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
        errors = []
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
                logo_binary = self._get_linkedin_organization_logo(
                    response_organizations
                )
                localized_name = response_organizations.get("name", {}).get(
                    "localized", {}
                )
                # The organization publishes its name in several languages:
                # the one of the user is preferred, and any of them is taken
                # rather than leaving the account without a name.
                organizations_data.append(
                    {
                        "id": response_organizations.get("id", False),
                        "localizedName": (
                            localized_name.get(self.env.user.lang)
                            or localized_name.get("en_US")
                            or next(iter(localized_name.values()), False)
                        ),
                        "vanityName": response_organizations.get("vanityName", False),
                        "logo": logo_binary,
                    }
                )
            else:
                error_message = self._linkedin_error_message(
                    response_organizations
                ) or _("Error obtaining information from the organization")
                account = (
                    self.env["social.account"]
                    .sudo()
                    .with_context(active_test=False)
                    .search(
                        [
                            (
                                "remote_ref",
                                "=",
                                f"{_URN_ORGANIZATION_LINKEDIN}{organization_id}",
                            ),
                        ],
                        limit=1,
                    )
                )
                if account:
                    account.message_post(body=error_message)
                errors.append(error_message)
        if errors and not organizations_data:
            raise UserError("\n".join(errors))
        return organizations_data

    def _create_account_linkedin(self, client_id, client_secret, token):
        """Create or update the accounts of the organizations of this token.

        An existing account is only reused when the current user is allowed
        to associate it, and it is reactivated if it was archived.
        """
        if not isinstance(token, dict):
            raise UserError(
                _(
                    "Creating account: %(error)s",
                    error=self._linkedin_error_message(token),
                )
            )
        access_token = token.get("access_token", False)
        if not access_token:
            raise UserError(
                _(
                    "Creating account: LinkedIn answered without an "
                    "access token. %(error)s",
                    error=self._linkedin_error_message(token),
                )
            )
        # Every wizard of this user holding these credentials is dropped at the
        # end, since the flow they started is over; the organizations are read
        # from the account they point at, which is the same one for all of them
        # because two accounts cannot share an application.
        wizards = (
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
            wizards.account_id._get_account_linkedin(access_token)
            if wizards
            else self._get_account_linkedin(access_token)
        )
        expire_token = date.today() + timedelta(days=token.get("expires_in", 0) / 86400)
        expire_refresh_token = date.today() + timedelta(
            seconds=token.get("refresh_token_expires_in", 0)
        )
        accounts = self.browse()
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
                "remote_ref": remote_ref,
                "last_update_account": fields.Datetime.now(),
                "linkedin_granted_scopes": self._linkedin_normalize_scopes(
                    token.get("scope")
                ),
            }
            if not social_account:
                values_data.update(
                    {
                        "media_id": self.env.ref(
                            "social_media_linkedin.social_media_linkedin"
                        ).id,
                    }
                )
                accounts |= self.sudo().create(
                    dict(values_data, user_id=self.env.user.id)
                )
            else:
                if not social_account.active:
                    values_data["active"] = True
                social_account.sudo().write(values_data)
                accounts |= social_account
        wizards.unlink()
        accounts._trigger_initial_sync()

    def _linkedin_normalize_scopes(self, raw_scopes):
        """Return the scopes of a LinkedIn answer as a comma separated string.

        The token endpoint separates them with spaces and the introspection
        one with commas, so both are accepted and stored the same way. They
        are stored with a comma because a scope is read as a whole, and a
        list of names holding underscores is unreadable when only spaces
        separate them.

        :param raw_scopes: the ``scope`` value answered by LinkedIn.
        :rtype: str
        """
        if not raw_scopes:
            return ""
        return ", ".join(sorted(str(raw_scopes).replace(",", " ").split()))

    def _get_linkedin_authorization_scopes(self):
        """Return the scopes to request when authorizing this account.

        What the installed modules need is always asked for: an account
        associated before a module was installed was granted a token that
        knows nothing of its scopes, and asking again for what it already
        holds would keep it that way forever. What LinkedIn granted it is
        added on top, so a scope edited by hand once a new product is
        enabled on the application survives the next authorization.

        :rtype: list
        """
        self.ensure_one()
        scopes = self.media_id._get_linkedin_scopes()
        granted = self.sudo().linkedin_granted_scopes or ""
        return scopes + [
            scope
            for scope in (raw.strip() for raw in granted.split(","))
            if scope and scope not in scopes
        ]

    def _has_linkedin_scope(self, scope):
        """Whether the token of this account was granted ``scope``.

        An account whose scopes are unknown answers ``True``: they are only
        known once LinkedIn reported them, and a check meant to give a clearer
        error must not block an account that works.

        :param scope: the LinkedIn scope to look for.
        :rtype: bool
        """
        self.ensure_one()
        granted = self.sudo().linkedin_granted_scopes
        if not granted:
            return True
        return scope in [granted_scope.strip() for granted_scope in granted.split(",")]

    def _check_linkedin_scopes(self, scopes):
        """Raise a readable error when a scope needed by a feature is missing.

        LinkedIn answers a bare ``403`` when a call needs a scope the token
        was not granted, which says nothing about what to do; the account has
        to be associated again once the product is enabled.

        :param scopes: the scopes the feature about to be called needs.
        """
        self.ensure_one()
        missing = [scope for scope in scopes if not self._has_linkedin_scope(scope)]
        if missing:
            raise UserError(
                _(
                    "The LinkedIn account %(account)s was not authorized for "
                    "%(scopes)s. Enable the matching product on the LinkedIn "
                    "application and associate the account again.",
                    account=self.name,
                    scopes=", ".join(missing),
                )
            )

    def _validate_linkedin_access_token(self, access_token):
        """Ask LinkedIn whether the given access token is still active.

        The answer also carries the scopes the token was granted, which are
        stored on the way: they are the only reliable picture of what this
        account may do on LinkedIn.

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
            scopes = self._linkedin_normalize_scopes(response.get("scope"))
            if scopes and account_sudo.linkedin_granted_scopes != scopes:
                account_sudo.linkedin_granted_scopes = scopes
            return True
        return False

    def validate_access_token(self):
        """Renew the token of this account when its dates say it is due.

        A token is treated as expired a few days ahead of its date: the check
        runs before every publication and on the schedule of the updates cron,
        and a token renewed at the last moment is one that a post planned for
        the weekend would not find.
        """
        res = super().validate_access_token()
        if self.media_id.media_type == "linkedin":
            timezone = pytz.timezone(self.env.user.tz or "UTC")
            ctx = dict(self.env.context)
            today = datetime.now(tz=timezone).date()
            margin = today + timedelta(days=_TOKEN_MARGIN_DAYS_LINKEDIN)
            expired = (
                self.expire_access_token_date and self.expire_access_token_date < margin
            ) or (
                self.refresh_token_expires_in and self.refresh_token_expires_in < today
            )
            if expired or ctx.get("check_remote_token", False):
                is_valid_token_access = self._validate_linkedin_access_token(
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
                    self._notify_valid_token_linkedin()
            elif not ctx.get("not_notify", False):
                self._notify_valid_token_linkedin()

        return res

    def _notify_valid_token_linkedin(self):
        self._notify_user_client(
            notif_type="social_form_success",
            notif_message=_("The token is valid."),
            media="linkedin",
            account_name=self.name or "LinkedIn",
        )

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
            "count": _POSTS_PAGE_SIZE_LINKEDIN,
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
                    "The publications could not be read from LinkedIn: %(error)s",
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

    def _get_all_posts(self):
        """Read the whole feed of the account, page by page.

        A single page is not the feed: LinkedIn documents that a page may
        carry fewer posts than asked while more are left, so the end is only
        reached on an empty page. Knowing whether the end was reached is what
        makes it safe to conclude that a post missing from the answer was
        deleted, hence the flag returned along the posts.

        :return: the posts of the account and whether the feed was read whole.
        :rtype: tuple(list, bool)
        """
        self.ensure_one()
        posts = []
        seen_urns = set()
        for page in range(_POSTS_MAX_PAGES_LINKEDIN):
            page_posts = self._get_posts(
                params_fields=["start"],
                params_values={"start": page * _POSTS_PAGE_SIZE_LINKEDIN},
                add_values=True,
            )
            if not page_posts:
                return posts, True
            for post in page_posts:
                if post["id"] not in seen_urns:
                    seen_urns.add(post["id"])
                    posts.append(post)
        _logger.warning(
            "The feed of the LinkedIn account %s is longer than %s pages, it "
            "was read partially and the deleted posts are not looked for",
            self.name,
            _POSTS_MAX_PAGES_LINKEDIN,
        )
        return posts, False

    def _get_linkedin_images_download_url(self, image_urns):
        """Return the download URL of each image.

        The Posts API only answers the URN of the images of a post, so the
        Images API is asked for the URL to download them from. It is a
        ``BATCH_GET``, capped by LinkedIn at ``_BATCH_GET_MAX_IDS_LINKEDIN``
        elements, so the URNs go in chunks of that size. A failure is logged
        instead of raised, and only loses its own chunk: the images are a
        complement of the post and must not stop the statistics pass.

        :param image_urns: The URNs of the images to resolve.
        :return: The download URL by image URN.
        :rtype: dict
        """
        urns = list(image_urns)
        if not urns:
            return {}
        headers = self.media_id._get_linkedin_headers(
            self.sudo().access_token, x_restli_method="BATCH_GET"
        )
        download_urls = {}
        for index in range(0, len(urns), _BATCH_GET_MAX_IDS_LINKEDIN):
            batch = urns[index : index + _BATCH_GET_MAX_IDS_LINKEDIN]
            response = self._request_linkedin(
                endpoint="/images",
                headers=headers,
                params_fields=["ids"],
                params_values={"ids": batch},
                return_json=False,
            )
            if response.status_code != 200:
                _logger.warning(
                    "Could not read the images of LinkedIn: %s",
                    self._linkedin_error_message(response),
                )
                continue
            download_urls.update(
                {
                    urn: image.get("downloadUrl")
                    for urn, image in response.json().get("results", {}).items()
                    if image.get("downloadUrl")
                }
            )
        return download_urls

    def _query_string_bytes(self, params_fields, params_values):
        """Return what the given query parameters weigh once encoded.

        Tells how much room is left for the URNs of a statistics call, the
        only part of the query string that can be split.

        :rtype: int
        """
        return sum(
            len(social_url_encode(param_field, params_values).encode())
            # The "&" joining this parameter to the next one.
            + 1
            for param_field in params_fields
        )

    def _filter_urns(self, posts, urn_prefix):
        """Return the URNs of the posts of one kind, in the order given.

        :param posts: the posts as the Posts API answered them.
        :param urn_prefix: ``urn:li:share:`` or ``urn:li:ugcPost:``.
        :rtype: list
        """
        return [
            post["id"]
            for post in posts
            if post.get("id") and post["id"].startswith(urn_prefix)
        ]

    def _parse_share_statistics(self, payload, urn_key):
        """Read the answer of ``organizationalEntityShareStatistics``.

        The shares and the UGC posts are asked for with a parameter of their
        own but answer the very same block, only the key naming the entity
        changes. An entity with no activity at all is left out of the answer,
        and is therefore left out of the result: its figures are all zero.

        :param payload: the parsed answer of LinkedIn.
        :param urn_key: ``share`` or ``ugcPost``.
        :return: Statistics tuple by post URN.
        :rtype: dict
        """
        statistics = {}
        for element in payload.get("elements", []):
            urn = element.get(urn_key)
            if not urn:
                continue
            totals = element.get("totalShareStatistics", {})
            statistics[urn] = (
                totals.get("clickCount", 0),
                totals.get("likeCount", 0),
                totals.get("commentCount", 0),
                totals.get("shareCount", 0),
                totals.get("engagement", 0),
                totals.get("impressionCount", 0),
            )
        return statistics

    def _get_entity_share_statistics(
        self,
        urns,
        param_field,
        urn_key,
        error_label,
        params_fields=None,
        params_values=None,
    ):
        """Read ``organizationalEntityShareStatistics`` for the given URNs.

        LinkedIn takes every URN in the query string and documents that
        endpoint as not paginated, so the URNs are split into as many calls
        as the 4 KB limit of the query string needs.

        :param urns: the URNs to read the statistics of.
        :param param_field: ``shares`` or ``ugcPosts``.
        :param urn_key: the key naming the entity in the answer.
        :param error_label: what to call the call in the error message.
        :return: Statistics tuple by post URN.
        :rtype: dict
        """
        data = {}
        params_fields = list(params_fields or [])
        params_values = dict(params_values or {})
        fixed_bytes = self._query_string_bytes(params_fields, params_values)
        for batch in _batch_urns_by_url_size(urns, param_field, fixed_bytes):
            response = self._request_linkedin(
                endpoint="/organizationalEntityShareStatistics",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.sudo().access_token, x_restli_method="FINDER"
                ),
                params_fields=params_fields + [param_field],
                params_values={**params_values, param_field: [",".join(batch)]},
                linkedin_v2=True,
                return_json=False,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "%(label)s: %(error)s",
                        label=error_label,
                        error=self._linkedin_error_message(response),
                    )
                )
            data.update(self._parse_share_statistics(response.json(), urn_key))
        return data

    def _linkedin_read_watched_figures(self):
        """Ask LinkedIn for the figures the update check compares.

        Asked with ``timeIntervals`` and no URN, the endpoint answers one
        bucket per day covering the whole organization instead of one entry per
        publication. That is one call whatever the number of publications,
        which is what makes it worth watching to know whether anything moved.

        The daily buckets are watched instead of the lifetime totals the same
        endpoint answers without ``timeIntervals``, because those totals lag
        behind. Verified against the real account: a reaction given an hour and
        a half earlier was already counted in the buckets while the lifetime
        figures still ignored it, and the sum of the twelve monthly buckets
        matched the lifetime answer to the unit on every figure except that one
        reaction. The lifetime totals are therefore useless as a signal of
        freshness, whatever else they are good for.

        Those figures are not the sum of what Odoo imported and are not meant
        to be compared against it: LinkedIn counts publications older than the
        import and stops counting the ones that were deleted. They are only
        ever compared against the previous reading of themselves.

        Only the import needs to ask: the check of the cron reads the buckets
        the refresh sweep of its own pass already brought back. The window is
        the one the sweep reads, trimmed to the days the check compares, so
        the mark left here is the one that pass would have left.

        :return: the watched figures by day, empty when LinkedIn reports none.
        :rtype: dict
        """
        self.ensure_one()
        start_time, end_time = self._linkedin_statistics_interval(
            *self._linkedin_refresh_window()
        )
        return self._linkedin_watched_figures(
            self._get_linkedin_daily_statistics(start_time, end_time, "DAY")
        )

    @api.model
    def _linkedin_check_days(self):
        """Return the ISO days the update check compares, today included.

        ``_UPDATE_CHECK_DAYS_LINKEDIN`` days counting today, keyed the same
        way ``_get_linkedin_daily_statistics`` keys its buckets so the two can
        be intersected without converting anything.

        This window is one day narrower than the one the refresh rewrites, and
        deliberately so: the checkpoints already stored were written with these
        days, and comparing them against a wider set would read the extra day
        as a day that appeared with activity, flagging every active account at
        once on the first pass after deploying.

        :rtype: set
        """
        today = fields.Date.today()
        return {
            (today - timedelta(days=offset)).isoformat()
            for offset in range(_UPDATE_CHECK_DAYS_LINKEDIN)
        }

    @api.model
    def _linkedin_watched_figures(self, buckets):
        """Return the watched figures of the days the check compares.

        Trims the buckets to ``_linkedin_check_days`` and keeps only
        ``_UPDATE_CHECK_FIGURES_LINKEDIN`` out of each one: the engagement is
        left out because it is a ratio LinkedIn recomputes, so it moves
        without anything having happened on the page.

        Pure on purpose: this is what the check used to ask LinkedIn for and
        it now reads from the buckets the refresh of the same pass already
        brought back.

        :param buckets: the buckets as ``_get_linkedin_daily_statistics``
            builds them, keyed by ISO day.
        :return: the watched figures by day, empty when there are none.
        :rtype: dict
        """
        days = self._linkedin_check_days()
        return {
            day: tuple(figures[index] for index in _UPDATE_CHECK_FIGURES_LINKEDIN)
            for day, figures in (buckets or {}).items()
            if day in days
        }

    @api.model
    def _linkedin_statistics_checkpoint(self, statistics):
        """Return the stored form of the daily buckets of a page.

        Kept as sorted JSON so the value is stable whatever order LinkedIn
        answered the buckets in.

        :param statistics: the buckets as ``_linkedin_watched_figures`` returns
            them, keyed by the ISO day. A string and never a ``date``: this very
            dictionary travels through ``json.dumps``, so changing the key
            invalidates every checkpoint already stored.
        :return: the value to store, empty when there is nothing to compare.
        :rtype: str
        """
        if not statistics:
            return ""
        return json.dumps(
            {period: list(figures) for period, figures in statistics.items()},
            sort_keys=True,
        )

    @api.model
    def _linkedin_statistics_snapshot(self, checkpoint):
        """Read back a checkpoint, ignoring anything that is not one.

        The value comes from a stored column, so it is validated instead of
        trusted: a checkpoint written by an older version of this check, or edited
        by hand, must read as "no baseline yet" rather than compare wrongly.

        :param checkpoint: the stored value.
        :return: the buckets by day, empty when there is nothing usable.
        :rtype: dict
        """
        if not checkpoint:
            return {}
        try:
            snapshot = json.loads(checkpoint)
        except ValueError:
            return {}
        if not isinstance(snapshot, dict):
            return {}
        return {
            period: figures
            for period, figures in snapshot.items()
            if is_list_of(figures, (int, float))
        }

    @api.model
    def _linkedin_statistics_moved(self, previous, current):
        """Tell whether the daily buckets carry activity the last import missed.

        Buckets are compared day by day and never as a whole: the window slides,
        so the oldest day of the previous reading is gone from this one, and
        comparing the two sets would report a change every single day.

        A day missing from the previous reading only counts when it carries
        activity. LinkedIn answers a bucket of zeros for a day with nothing on it,
        and the day in progress starts as one of those: announcing it would mean
        announcing updates every midnight.

        A day gone from this reading is ignored: it aged out of the window, which
        is not activity.

        :param previous: the buckets of the last import.
        :param current: the buckets read now.
        :return: whether anything moved.
        :rtype: bool
        """
        if not previous:
            return False
        for period, figures in current.items():
            stored = previous.get(period)
            if stored is None:
                if any(figures):
                    return True
            elif list(stored) != list(figures):
                return True
        return False

    def _get_share_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
    ):
        """Read the statistics of the share posts among the given ones.

        :return: Statistics tuple by share URN.
        :rtype: dict
        """
        if not posts:
            return {}
        return self._get_entity_share_statistics(
            self._filter_urns(posts, _URN_SHARE_LINKEDIN),
            "shares",
            "share",
            _("The statistics of the shared publications could not be read"),
            params_fields=params_fields,
            params_values=params_values,
        )

    def _get_ugc_share_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
    ):
        """Read the statistics of the UGC posts among the given ones.

        Same endpoint as the shares, asked with the ``ugcPosts`` parameter.
        It is what brings the clicks, the shares, the engagement and the
        impressions of a UGC post: ``socialActions`` only knows its likes and
        its comments.

        :return: Statistics tuple by UGC post URN.
        :rtype: dict
        """
        if not posts:
            return {}
        return self._get_entity_share_statistics(
            self._filter_urns(posts, _URN_UGC_POST_LINKEDIN),
            "ugcPosts",
            "ugcPost",
            _("The statistics of the publications could not be read"),
            params_fields=params_fields,
            params_values=params_values,
        )

    def _get_ugc_posts_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
    ):
        """Read the likes and the comments of the UGC posts of the feed.

        LinkedIn documents ``socialActions`` as the up-to-date source of
        those two counts, the ones the feed shows, which is why they are read
        apart from the rest of the figures. It is asked for in as many calls
        as the 4 KB limit of the query string needs.

        :return: ``(likes, comments)`` by UGC post URN.
        :rtype: dict
        """
        data = {}
        if not posts:
            return data
        params_fields = list(params_fields or [])
        params_values = dict(params_values or {})
        fixed_bytes = self._query_string_bytes(params_fields, params_values)
        urns = self._filter_urns(posts, _URN_UGC_POST_LINKEDIN)
        for batch in _batch_urns_by_url_size(urns, "ids", fixed_bytes):
            response = self._request_linkedin(
                endpoint="/socialActions",
                headers=self.media_id._get_linkedin_headers(
                    access_token=self.sudo().access_token
                ),
                params_fields=params_fields + ["ids"],
                params_values={**params_values, "ids": [",".join(batch)]},
                return_json=False,
                linkedin_v2=True,
            )
            if response.status_code != 200:
                raise UserError(
                    _(
                        "The likes and the comments of the publications could not be "
                        "read: %(error)s",
                        error=self._linkedin_error_message(response),
                    )
                )
            data.update(
                {
                    urn_id: (
                        post_reaction.get("likesSummary", {}).get("totalLikes", 0),
                        post_reaction.get("commentsSummary", {}).get(
                            "aggregatedTotalComments", 0
                        ),
                    )
                    for urn_id, post_reaction in response.json()
                    .get("results", {})
                    .items()
                }
            )
        return data

    def _get_entity_statistics(
        self,
        posts=None,
        params_fields=None,
        params_values=None,
    ):
        """Merge the statistics of the share posts and of the UGC posts.

        Three calls are needed. ``organizationalEntityShareStatistics``
        answers the whole block of figures, but the shares and the UGC posts
        are asked for with a parameter of their own. ``socialActions`` is
        read on top of it because LinkedIn documents its likes and its
        comments as the up-to-date ones, the ones the feed shows.

        :return: Statistics tuple by post URN.
        :rtype: dict
        """
        if self.media_type != "linkedin":
            return {}
        if not posts:
            return {}
        if not params_fields:
            params_fields = ["q", "organizationalEntity"]
        if not params_values:
            params_values = {
                "q": "organizationalEntity",
                "organizationalEntity": f"{_URN_ORGANIZATION_LINKEDIN}"
                f"{self.linkedin_account_id}",
            }
        entity_params = {
            "params_fields": list(params_fields),
            "params_values": dict(params_values),
        }
        data = self._get_share_statistics(posts=posts, **entity_params)
        data.update(self._get_ugc_share_statistics(posts=posts, **entity_params))
        # ``socialActions`` takes neither the criteria of the share finder
        # nor the organization it is about.
        social_actions = self._get_ugc_posts_statistics(
            posts=posts,
            params_fields=[
                param_field
                for param_field in params_fields
                if param_field not in _FINDER_PARAMS_LINKEDIN
            ],
            params_values={
                key: value
                for key, value in params_values.items()
                if key not in _FINDER_PARAMS_LINKEDIN
            },
        )
        for urn, (likes, comments) in social_actions.items():
            clicks, __, __, shares, engagement, impressions = data.get(
                urn, (0, 0, 0, 0, 0, 0)
            )
            data[urn] = (clicks, likes, comments, shares, engagement, impressions)
        return data

    def _notify_statistics_failure(self, error):
        """Tell the user why the statistics of this account were not read.

        :param error: whatever was raised while refreshing the account.
        """
        self.ensure_one()
        _logger.exception(
            "Error updating the posts statistics of the LinkedIn account %s",
            self.name,
        )
        self._notify_user_client(
            notif_type="social_kanban_danger",
            notif_message=self._linkedin_error_message(error),
            media="linkedin",
            account_name=self.name,
        )

    @contextmanager
    def _statistics_guard(self):
        """Isolate the refresh of one account in its own savepoint.

        Reading a feed writes on the way: the publications gone from
        LinkedIn are marked as deleted before their statistics are even
        asked for. An error on what comes after must not leave those writes
        behind, nor stop the accounts still to refresh, so each account is
        rolled back on its own and the reason is told to the user.

        ``psycopg2.OperationalError`` with a concurrency pgcode is raised
        again on purpose, so the retry mechanism of Odoo still sees it.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                yield
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            self._notify_statistics_failure(error)
        except Exception as error:  # noqa: BLE001 - the API may fail in any way
            self._notify_statistics_failure(error)

    def _update_posts_statistics(self, post_id, domain):
        statistics = super()._update_posts_statistics(post_id, domain)
        if not self:
            account_ids = self.search([("media_type", "=", "linkedin")])
        elif any(val.media_type == "linkedin" for val in self):
            account_ids = self
        else:
            return statistics
        for account in account_ids:
            with account._statistics_guard():
                account._refresh_linkedin_posts(post_id=post_id)
        return self._get_account_statistics(statistics=statistics)

    def _full_resync(self):
        """Read the whole feed of the LinkedIn accounts and reconcile it.

        This is what the ordinary refresh used to do on every run. It is kept
        apart because reading a feed of thousands of publications costs one
        call per hundred, and the only thing that needs it is reconciling what
        was deleted on LinkedIn: the statistics are asked for by URN and Odoo
        already knows the URNs.

        :return: whatever the other connectors answer for their own accounts.
        """
        linkedin = self.filtered(lambda account: account.media_type == "linkedin")
        for account in linkedin:
            with account._statistics_guard():
                account._refresh_linkedin_posts(full_feed=True)
        return super(SocialAccount, self - linkedin)._full_resync()

    def _linkedin_refresh_window(self):
        """Return the days the refresh rewrites, both ends included.

        LinkedIn revises figures of days already past, so the last days are
        asked for again on every pass instead of being trusted as final. The
        width is the one the connector already uses for this same class of
        decision, ``_UPDATE_CHECK_DAYS_LINKEDIN``; the days before it stay as
        the last pass left them.

        :rtype: tuple
        """
        date_to = fields.Date.today()
        return date_to - timedelta(days=_UPDATE_CHECK_DAYS_LINKEDIN), date_to

    def _linkedin_backfill_window(self):
        """Return the widest range of days LinkedIn may answer, both included.

        The depth is LinkedIn's to decide, not the module's: the endpoint
        documents a rolling window of ``_STATISTICS_HISTORY_MONTHS_LINKEDIN``
        months, but not how much of it it serves by day. The whole window is
        asked for and whatever buckets come back are written, so two accounts
        may well end up with a different depth.

        :rtype: tuple
        """
        date_to = fields.Date.today()
        return (
            date_to - relativedelta(months=_STATISTICS_HISTORY_MONTHS_LINKEDIN),
            date_to,
        )

    def _backfill_statistics(self):
        linkedin = self.filtered(lambda account: account.media_type == "linkedin")
        if linkedin:
            linkedin._snapshot_statistics(*linkedin._linkedin_backfill_window())
        return super(SocialAccount, self - linkedin)._backfill_statistics()

    def _linkedin_refresh_statistics(self):
        """Rewrite the last days of these accounts and keep what was read.

        Same sweep as ``_snapshot_statistics`` over the refresh window, except
        that the buckets are kept instead of being thrown away once written:
        the check of the same pass compares against them rather than asking
        the finder for the very same days a few milliseconds later.

        An account whose reading failed is simply absent from the answer. Its
        savepoint was rolled back and its responsible user already told, so
        there is nothing left to compare for it in this pass.

        :return: the buckets read, keyed by account id.
        :rtype: dict
        """
        date_from, date_to = self._linkedin_refresh_window()
        buckets_by_account = {}
        for account in self.filtered(lambda account: account.media_type == "linkedin"):
            if not account.linkedin_account_id:
                # The finder is asked for an organization, so an account
                # without one cannot even be asked.
                continue
            with account._statistics_guard():
                buckets_by_account[account.id] = account._snapshot_linkedin_statistics(
                    date_from, date_to
                )
        return buckets_by_account

    def _refresh_statistics(self):
        linkedin = self.filtered(lambda account: account.media_type == "linkedin")
        if linkedin:
            linkedin._linkedin_refresh_statistics()
        return (
            bool(linkedin)
            or super(SocialAccount, self - linkedin)._refresh_statistics()
        )

    def _snapshot_statistics(self, date_from, date_to):
        """Write the daily figures LinkedIn reports for these accounts.

        The finder is asked once per account with ``timeGranularityType=DAY``
        and every bucket it answers becomes a row of the time series. Nothing
        is invented for the days it does not report: a day with no bucket
        leaves no row, and LinkedIn decides on its own how far back it
        answers, so two accounts may end up with a different depth.

        Each account goes in its own savepoint. A ``403`` on one of them is
        told to the user and the sweep carries on, so the rows already written
        for the other accounts stay written.

        :return: whatever the other connectors answer for their own accounts.
        """
        linkedin = self.filtered(lambda account: account.media_type == "linkedin")
        for account in linkedin:
            if not account.linkedin_account_id:
                # The finder is asked for an organization, so an account
                # without one cannot even be asked: the same guard the import
                # makes before walking the feed.
                continue
            with account._statistics_guard():
                account._snapshot_linkedin_statistics(date_from, date_to)
        return super(SocialAccount, self - linkedin)._snapshot_statistics(
            date_from, date_to
        )

    def _linkedin_statistics_interval(self, date_from, date_to):
        """Return the range of days as the timestamps the finder takes.

        The interval ends the day **after** ``date_to``: LinkedIn takes the
        end of a time interval as exclusive and normalizes it to the day, so
        asking up to ``date_to`` itself would leave out the last day of the
        range, which on the refresh is the one that moves.

        :param date_from: first day asked for, included.
        :param date_to: last day asked for, included.
        :return: the two timestamps, ``(None, None)`` on an empty range.
        :rtype: tuple
        """
        self.ensure_one()
        start = fields.Date.to_date(date_from)
        end = fields.Date.to_date(date_to)
        if not (start and end) or start > end:
            return None, None
        start_time, end_time = self._get_default_filter_date(
            datetime.combine(start, datetime.min.time()),
            datetime.combine(end + timedelta(days=1), datetime.min.time()),
        )
        return epoch_milliseconds(start_time), epoch_milliseconds(end_time)

    def _snapshot_linkedin_statistics(self, date_from, date_to):
        """Write the rows of one account for the given range of days.

        The buckets are given back as they were read, keyed by the ISO day and
        with the tuple ``_get_linkedin_daily_statistics`` builds, so the caller
        of a sweep can compare them without asking the finder a second time.

        :param date_from: first day to write, included.
        :param date_to: last day to write, included.
        :return: the buckets read, keyed by ISO day.
        :rtype: dict
        """
        self.ensure_one()
        start_time, end_time = self._linkedin_statistics_interval(date_from, date_to)
        if not (start_time and end_time):
            return {}
        buckets = self._get_linkedin_daily_statistics(start_time, end_time, "DAY")
        self._write_statistics_rows(
            {
                day: self._linkedin_statistics_values(figures)
                for day, figures in buckets.items()
            }
        )
        return buckets

    @api.model
    def _linkedin_statistics_values(self, figures):
        """Return the figures of one publication as its statistics fields.

        :param figures: the statistics tuple as ``_parse_share_statistics``
            builds it, empty when LinkedIn reported none for that URN.
        :rtype: dict
        """
        clicks, likes, comments, shares, engagement, impressions = figures or (
            0,
            0,
            0,
            0,
            0,
            0,
        )
        return {
            "click_count": clicks,
            "like_count": likes,
            "comment_count": comments,
            "share_count": shares,
            "engagement": engagement,
            "impression_count": impressions,
        }

    def _refresh_linkedin_posts(self, post_id=None, full_feed=False):
        """Import the publications of this account and their statistics.

        Three ways in, and what the feed is read for is what tells them apart:

        - ``post_id``: one publication, asked for by its URN.
        - ``full_feed``: the whole feed, page by page, which is the only way to
          know that a publication was deleted on LinkedIn.
        - neither: the ordinary refresh. **The feed is not walked.** One page
          sorted by last modification brings what is new or edited, and the
          statistics are asked for by URN over that page plus the URNs Odoo
          already stores for the account. A publication whose content did not
          change does not need to be read again: nothing can change it without
          LinkedIn moving its last modification date.

        :param post_id: the URN of the only publication to refresh.
        :param full_feed: whether to walk the whole feed and reconcile it.
        """
        self.ensure_one()
        PostAccount = self.env["social.post.account"]
        self.with_context(not_notify=True).validate_access_token()
        if not self.linkedin_account_id:
            return
        feed_is_complete = False
        if post_id:
            ugc_posts = self._get_posts(
                params_fields=["ids"], params_values={"ids": [post_id]}
            )
        elif full_feed:
            ugc_posts, feed_is_complete = self._get_all_posts()
        else:
            # Fresh literals: with ``add_values`` the finder parameters are
            # merged into the given ones in place.
            ugc_posts = self._get_posts(
                params_fields=["sortBy"],
                params_values={"sortBy": "LAST_MODIFIED"},
                add_values=True,
            )
        discovered = [post["id"] for post in ugc_posts if post.get("id")]
        # A post missing from the answer is only gone when the whole feed was
        # read: on a partial answer the same search would mark live
        # publications as deleted.
        if feed_is_complete:
            PostAccount.search(
                [
                    ("remote_ref", "not in", discovered),
                    ("remote_ref", "!=", False),
                    ("account_id", "=", self.id),
                    ("state", "!=", "deleted"),
                ]
            ).write({"post_account_url": False, "state": "deleted"})
        # The publications Odoo knows and the answer did not bring. Their
        # figures are refreshed all the same, by URN, which is what spares
        # reading the feed. ``sudo`` because the publications are scoped to
        # their responsible and this also runs from a cron, and ``active_test``
        # off because an archived publication is still online on LinkedIn.
        stale_lines = PostAccount
        if not post_id:
            stale_lines = (
                PostAccount.sudo()
                .with_context(active_test=False)
                .search(
                    [
                        ("account_id", "=", self.id),
                        ("remote_ref", "!=", False),
                        ("remote_ref", "not in", discovered),
                        ("state", "!=", "deleted"),
                    ]
                )
            )
        post_reactions = self._get_entity_statistics(
            posts=[{"id": urn} for urn in discovered + stale_lines.mapped("remote_ref")]
        )
        post_accounts = []
        post_accounts_by_urn = {}
        for existing in (
            PostAccount.sudo()
            .with_context(active_test=False)
            .search([("remote_ref", "in", discovered)])
        ):
            post_accounts_by_urn.setdefault(existing.remote_ref, existing)
        for ugc_post in ugc_posts:
            post_account = post_accounts_by_urn.get(ugc_post.get("id"), PostAccount)
            content = ugc_post.get("content", {})
            ugc_post_urn = ugc_post.get("id")
            data = {
                "remote_ref": ugc_post_urn,
                "post_account_url": f"{_URL_FEED_UPDATE_LINKEDIN}{ugc_post_urn}",
                "message": ugc_post.get("commentary", ""),
                "account_id": self.id,
                "published_date": datetime.fromtimestamp(
                    (
                        ugc_post.get("publishedAt")
                        or int(datetime.now(tz=pytz.UTC).timestamp() * 1000)
                    )
                    / 1000
                ),
                "actor_urn": ugc_post.get("author", False),
                "has_video": str(content.get("media", {}).get("id", "")).startswith(
                    _URN_VIDEO_LINKEDIN
                ),
                "state": "posted",
                **self._linkedin_statistics_values(post_reactions.get(ugc_post_urn)),
            }
            attach_images = post_account._get_assets_save(content, account=self)
            if post_account:
                post_account._remove_assets_deleted(content)
            if attach_images:
                data.update({"image_ids": attach_images})
            if not post_account:
                post_accounts.append(Command.create(data))
            else:
                post_accounts.append(Command.update(post_account.id, data))
        for line in stale_lines:
            post_accounts.append(
                Command.update(
                    line.id,
                    self._linkedin_statistics_values(
                        post_reactions.get(line.remote_ref)
                    ),
                )
            )
        update_account_data = {
            "post_account_ids": post_accounts,
            "need_update": False,
        }
        # The totals of the account are the sum of every publication, so they
        # are only recomputed when every publication was asked about:
        # refreshing a single one would otherwise leave the account with the
        # statistics of that one alone.
        if not post_id and post_reactions:
            update_account_data.update(self._filter_statistics(post_reactions))
        # The check for updates compares the daily figures of the page against
        # the ones of the last import, so the import is what leaves the mark to
        # compare with. Refreshing a single publication says nothing about the
        # rest of the page.
        if not post_id:
            update_account_data[
                "linkedin_statistics_checkpoint"
            ] = self._linkedin_statistics_checkpoint(
                self._linkedin_read_watched_figures()
            )
        self.write(update_account_data)

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

    def _get_linkedin_daily_statistics(self, start_time, end_time, granularity):
        """Return the statistics of this account by day.

        The ``organizationalEntity`` finder answers one element per bucket of
        ``timeGranularityType`` when it is not restricted to a list of shares,
        each one carrying the ``timeRange`` it covers. The bucket of the day
        in progress is not reported yet, which is exactly why the statistics
        are keyed by the day they cover instead of being returned as a plain
        list.

        The key is the ISO day of ``timeRange.start``, as ``2025-01-02``. A
        string and not a ``date``, because the caller that watches the page
        for updates stores this very dictionary as JSON.

        :rtype: dict
        """
        response = self._request_linkedin(
            endpoint="/organizationalEntityShareStatistics",
            headers=self.media_id._get_linkedin_headers(
                access_token=self.sudo().access_token, x_restli_method="FINDER"
            ),
            params_fields=["q", "organizationalEntity", "timeIntervals", "count"],
            params_values={
                "q": "organizationalEntity",
                "organizationalEntity": f"{_URN_ORGANIZATION_LINKEDIN}"
                f"{self.linkedin_account_id}",
                "timeIntervals": f"(timeRange:(start:{start_time},"
                f"end:{end_time})"
                f",timeGranularityType:{granularity})",
                "count": 100,
            },
            linkedin_v2=True,
            return_json=False,
        )
        if response.status_code != 200:
            raise UserError(
                _(
                    "Error reading the statistics of the LinkedIn account: "
                    "%(error)s",
                    error=self._linkedin_error_message(response),
                )
            )
        statistics = {}
        for element in response.json().get("elements", []):
            bucket_start = element.get("timeRange", {}).get("start")
            if not bucket_start:
                continue
            share_statistics = element.get("totalShareStatistics", {})
            day = datetime.fromtimestamp(bucket_start / 1000).date().isoformat()
            bucket = (
                share_statistics.get("clickCount", 0),
                share_statistics.get("likeCount", 0),
                share_statistics.get("commentCount", 0),
                share_statistics.get("shareCount", 0),
                share_statistics.get("engagement", 0),
                share_statistics.get("impressionCount", 0),
            )
            # Several buckets of the same day are added up instead of
            # overwriting each other. LinkedIn answers one bucket per
            # granularity unit, so this only bites when the unit asked for is
            # wider than a day and it reports it split.
            previous = statistics.get(day)
            statistics[day] = (
                bucket
                if previous is None
                else tuple(
                    before + now for before, now in zip(previous, bucket, strict=True)
                )
            )
        return statistics

    def _run_check_media_updates(self):
        """Flag the LinkedIn accounts whose page moved since the last import.

        At most two calls per account, whatever the number of publications.
        The daily figures of the whole page are read first, because a change
        there is enough to know that something happened and spares the second
        call. Only when they did not move is the feed asked for its newest
        publication, which is what catches a post published outside Odoo that
        nobody has interacted with yet.

        The check never imports anything: it only turns on ``need_update``,
        and the import the user asks for is what turns it off and leaves the
        new figures to compare with. What it does write is the time series of
        the page, one row per account and day over the rewrite window, which
        is what the graph view reads.

        The answer of the previous connectors is not looked at. Each one
        checks its own accounts, so a connector that found updates does not
        silence the others.

        :return: whether new updates were found, by this connector or before.
        :rtype: bool
        """
        update = super()._run_check_media_updates()
        try:
            # The accounts waiting for their initial sync are left out: this
            # check writes ``need_update`` on the same row the import writes
            # its statistics on, and the import is what brings in the updates
            # it looks for. ``sudo`` because the cron record sets no user and
            # the accounts belong to every responsible.
            #
            # An account already announcing updates is left out too, and costs
            # no call at all: only the import clears the flag, so asking
            # LinkedIn again before the user imports can only confirm what the
            # dashboard already says. An account with no organization is left
            # out because the feed of one cannot even be asked for, the same
            # guard the import makes.
            # The time series is written for every account that can be
            # asked, ``need_update`` or not: the flag says the user has an
            # import pending, not that the figures of the page stopped
            # moving. ``_linkedin_refresh_statistics`` isolates each account
            # on its own, so one that answers an error does not stop the rest.
            #
            # The two searches keep their own domain on purpose. The sweep
            # cannot inherit the ``need_update`` of the check, or the series
            # would be left with holes on the very accounts that move the
            # most; and the check cannot drop it, or it would ask again about
            # accounts whose flag only an import clears. The sweep is the
            # wider of the two, so every account the check walks already has
            # its buckets read.
            buckets_by_account = (
                self.sudo()
                .search(
                    [
                        ("media_type", "=", "linkedin"),
                        ("pending_initial_sync", "=", False),
                        ("linkedin_account_id", "!=", False),
                    ]
                )
                ._linkedin_refresh_statistics()
            )
            account_ids = self.sudo().search(
                [
                    ("media_type", "=", "linkedin"),
                    ("pending_initial_sync", "=", False),
                    ("need_update", "=", False),
                    ("linkedin_account_id", "!=", False),
                ]
            )
            for account in account_ids:
                buckets = buckets_by_account.get(account.id)
                if buckets is None:
                    # The sweep failed on this account: its savepoint was
                    # rolled back and its responsible user already told, so
                    # asking again here would only fail again. The next pass
                    # retries it two hours later.
                    continue
                try:
                    # Each account in its own savepoint: the check writes, so
                    # a database error on one of them would otherwise abort the
                    # cursor and take down every account left, including the
                    # credentials the base already flagged.
                    with self.env.cr.savepoint():
                        update = account._check_linkedin_updates(buckets) or update
                except psycopg2.OperationalError as error:
                    if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                        raise
                    _logger.exception(
                        "Error checking the updates of the LinkedIn account %s",
                        account.id,
                    )
                except Exception:  # noqa: BLE001 - one account cannot stop the rest
                    _logger.exception(
                        "Error checking the updates of the LinkedIn account %s",
                        account.id,
                    )
        except psycopg2.OperationalError as error:
            # Re-raised so Odoo still retries the cron, and before the catch-all
            # below, which would otherwise swallow the raise above.
            if error.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                _logger.exception("Error checking the LinkedIn media updates")
            else:
                raise
        except Exception:  # noqa: BLE001 - a failed check must not stop the cron
            _logger.exception("Error checking the LinkedIn media updates")
        return update

    def _check_linkedin_updates(self, buckets):
        """Flag this account when its page moved since the last import.

        :param buckets: the buckets the refresh sweep of this pass read for
            this account, as ``_get_linkedin_daily_statistics`` builds them.
        :return: whether the account was flagged.
        :rtype: bool
        """
        self.ensure_one()
        statistics = self._linkedin_watched_figures(buckets)
        previous = self._linkedin_statistics_snapshot(
            self.linkedin_statistics_checkpoint
        )
        if not previous:
            # Nothing to compare with yet, on an account associated before this
            # check knew how to. Reading the page is what gives it its mark:
            # announcing updates on the very first run would announce them for
            # every account at once.
            self.linkedin_statistics_checkpoint = self._linkedin_statistics_checkpoint(
                statistics
            )
            return False
        if self._linkedin_statistics_moved(previous, statistics):
            # The mark is left alone on purpose: it belongs to the last
            # import, so the notice stays up until the user actually imports
            # instead of clearing itself on the next run.
            self._flag_linkedin_update()
            return True
        # The figures did not move, but a publication posted outside Odoo that
        # nobody has interacted with yet does not move them either.
        post_ids = self._get_posts(
            params_fields=["sortBy"],
            params_values={"sortBy": "LAST_MODIFIED"},
            add_values=True,
        )
        if not post_ids:
            return False
        # ``sudo`` because the publications are scoped to their responsible and
        # this also runs from the cron, and ``active_test`` off because
        # archiving a post archives its publications while they stay online on
        # LinkedIn: an archived row is known, not new.
        known = (
            self.env["social.post.account"]
            .sudo()
            .with_context(active_test=False)
            .search_count(
                [
                    ("remote_ref", "=", post_ids[0]["id"]),
                    ("remote_ref", "!=", False),
                    ("account_id", "=", self.id),
                ],
                limit=1,
            )
        )
        if known:
            return False
        self._flag_linkedin_update()
        return True

    def _flag_linkedin_update(self):
        """Announce on the dashboard that the account has updates to import."""
        self.ensure_one()
        if self.need_update:
            # Already announced. Writing again would touch the very row the
            # statistics import writes on, and push the bus message a second
            # time for something the dashboard already shows.
            return
        self.sudo().write({"need_update": True})
        self._need_update()
