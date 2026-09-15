# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin

import psycopg2
import pytz
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import split_every

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_linkedin_utils import (
    _BATCH_GET_MAX_IDS_LINKEDIN,
    _ENDPOINT_POSTS_LINKEDIN,
    _ENTITY_STATISTICS_LINKEDIN,
    _FINDER_PARAMS_LINKEDIN,
    _POSTS_PAGE_SIZE_LINKEDIN,
    _STATISTICS_HISTORY_MONTHS_LINKEDIN,
    _STATISTICS_MAX_BUCKETS_LINKEDIN,
    _TOKEN_MARGIN_DAYS_LINKEDIN,
    _UPDATE_CHECK_DAYS_LINKEDIN,
    _URL_AUTH_V2_LINKEDIN,
    _URL_REST_LINKEDIN,
    _URL_V2_LINKEDIN,
    _URN_ORGANIZATION_LINKEDIN,
    _URN_UGC_POST_LINKEDIN,
    _VIDEO_POLL_ATTEMPTS_LINKEDIN,
    _VIDEO_POLL_ATTEMPTS_MIN_LINKEDIN,
    _VIDEO_POLL_DELAY_LINKEDIN,
    _VIDEO_POLL_DELAY_MIN_LINKEDIN,
    _VIDEO_POLL_MAX_WAIT_LINKEDIN,
    _VIDEO_UPLOAD_PART_SIZE_LINKEDIN,
    _batch_urns_by_url_size,
    _linkedin_error_code,
    _linkedin_error_detail,
    _linkedin_is_credentials_error,
    datetime_from_epoch_milliseconds,
    epoch_milliseconds,
    linkedin_urn_id,
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
        return {
            **super()._fields_account_url(),
            "linkedin": (
                "https://www.linkedin.com/company/"
                f"{self.linkedin_account_id}/admin/dashboard/"
            ),
        }

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
        self._check_unique_credentials(
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
            ],
            _(
                "An account with this information "
                "already exists; please also check "
                "archived accounts."
            ),
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

    def action_rebuild_statistics_history(self):
        """Ask LinkedIn again for the daily figures of the whole period.

        The backfill runs once and is skipped from then on, so this is the way
        back for an account whose history was never read: the call of the
        association failed, or the series was truncated before the range was
        asked for in as many calls as it takes. It rebuilds the graph of the
        account and imports no publication.

        The rows are added up onto the account right after writing them, so
        the card shows what was just read instead of what the last pass left.
        """
        self.ensure_one()
        self._backfill_statistics(force=True)
        self._refresh_account_statistics()

    def _refresh_token(self):
        """Ask LinkedIn for a new access token with the refresh one.

        The credentials go in the body for the same reason as in
        :meth:`~._get_access_token_linkedin`.

        :return: the token response of LinkedIn.
        :rtype: dict
        """
        account_sudo = self.sudo()
        response = self._request_linkedin(
            method="POST",
            endpoint="/accessToken",
            token=True,
            headers=self.media_id._get_linkedin_headers(),
            data={
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
        values = self._linkedin_token_values(token)
        if not values["linkedin_granted_scopes"]:
            # LinkedIn does not always answer the scopes of a renewal, and an
            # empty answer is not a revocation: what the account was granted
            # is left as it is instead of being erased.
            del values["linkedin_granted_scopes"]
        self.sudo().write(values)
        return token

    def _linkedin_token_values(self, token):
        """Return the credential fields of a token LinkedIn answered.

        The expiry dates are counted from today, which is what LinkedIn
        measures its ``expires_in`` against, and both are written whatever the
        flow that read the token: a renewal and a fresh authorization leave
        the account in the same shape.

        :param token: the answer of the token endpoint.
        :rtype: dict
        """
        today = fields.Date.today()
        return {
            "access_token": token.get("access_token", False),
            "refresh_access_token": token.get("refresh_token", False),
            "expire_access_token_date": today
            + timedelta(seconds=token.get("expires_in", 0)),
            "refresh_token_expires_in": today
            + timedelta(seconds=token.get("refresh_token_expires_in", 0)),
            "linkedin_granted_scopes": self._linkedin_normalize_scopes(
                token.get("scope")
            ),
        }

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
            and self.refresh_token_expires_in < fields.Date.today()
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
        :return: The URN of every uploaded image, keyed by the identifier of
            the attachment that produced it.
        :rtype: dict
        """
        images_upload = {}
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
                data=image.raw,
                return_json=False,
            )
            if upload_image.status_code not in (200, 201):
                self._linkedin_raise_error(
                    _("The image could not be uploaded to LinkedIn"), upload_image
                )
            images_upload[str(image.id)] = image_urn
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

        The two numbers are bounded here and not where they are written: any
        user of ``base.group_system`` may set the parameters by hand, so the
        read site is the only place that sees every value they can take.

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
        delay = max(_VIDEO_POLL_DELAY_MIN_LINKEDIN, delay)
        attempts = max(
            _VIDEO_POLL_ATTEMPTS_MIN_LINKEDIN,
            min(attempts, int(_VIDEO_POLL_MAX_WAIT_LINKEDIN / delay)),
        )
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

        :return: The URN of every video once LinkedIn has processed it, keyed
            by the identifier of the attachment that produced it.
        :rtype: dict
        """
        videos_upload = {}
        for video in video_ids or []:
            video_data = video.raw
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
            videos_upload[str(video.id)] = video_urn
        return videos_upload

    def _linkedin_create_post(self, message, image_ids=None, video_ids=None):
        """Publish a post with its media through the Posts API.

        LinkedIn does not accept images and videos in the same post, so the
        images are ignored when the post carries a video.

        :return: The URN of the published post, or False when the account has
            no access token, together with the reference every medium got on
            LinkedIn, keyed by the identifier of its attachment. The caller
            stores that mapping on the publication, which is what tells a
            medium the social media knows about from one attached in Odoo.
        :rtype: tuple
        """
        if not self.sudo().access_token:
            return False, {}
        video_refs = self._linkedin_prepare_videos_for_post(video_ids)
        image_refs = (
            {} if video_refs else self._linkedin_prepare_images_for_post(image_ids)
        )
        video_urns = list(video_refs.values())
        image_urns = list(image_refs.values())
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
            endpoint=_ENDPOINT_POSTS_LINKEDIN,
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
        return response.headers.get("x-restli-id"), {**video_refs, **image_refs}

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

        The credentials travel form-encoded in the body of the POST, never in
        the query string, which servers and proxies write to their logs.

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
        return (
            client_id,
            client_secret,
            self._request_linkedin(
                method="POST",
                endpoint="/accessToken",
                timeout=10,
                token=True,
                data={
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": urljoin(self.get_base_url(), redirect_endpoint_uri),
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            ),
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
                linkedin_urn_id(organization["organization"])
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
        token_values = self._linkedin_token_values(token)
        accounts = self.browse()
        for organization in organizations:
            remote_ref = f"{_URN_ORGANIZATION_LINKEDIN}{organization.get('id')}"
            values_data = {
                "name": organization.get("localizedName", False),
                "username": organization.get("vanityName", False),
                "image_1920": organization.get("logo", False),
                "linkedin_client_id": client_id,
                "linkedin_secret": client_secret,
                **token_values,
                "remote_ref": remote_ref,
                "last_update_account": fields.Datetime.now(),
            }
            accounts |= self._associate_account(
                "linkedin",
                remote_ref,
                values_data,
                username=organization.get("vanityName", False),
                create_values={
                    "media_id": self.env.ref(
                        "social_media_linkedin.social_media_linkedin"
                    ).id,
                },
            )
        wizards.unlink()
        accounts._on_account_associated()

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
        return scopes + [
            scope
            for scope in self._linkedin_granted_scopes_list()
            if scope not in scopes
        ]

    def _linkedin_granted_scopes_list(self):
        """Return the scopes LinkedIn granted this account, as a list.

        They are stored as a comma separated string, so this is the one place
        that knows how to read them back.

        :rtype: list
        """
        self.ensure_one()
        granted = self.sudo().linkedin_granted_scopes or ""
        return [scope.strip() for scope in granted.split(",") if scope.strip()]

    def _has_linkedin_scope(self, scope):
        """Whether the token of this account was granted ``scope``.

        An account whose scopes are unknown answers ``True``: they are only
        known once LinkedIn reported them, and a check meant to give a clearer
        error must not block an account that works.

        :param scope: the LinkedIn scope to look for.
        :rtype: bool
        """
        self.ensure_one()
        # The field is the gate, not the parsed list: an account LinkedIn
        # never reported the scopes of has to keep working.
        if not self.sudo().linkedin_granted_scopes:
            return True
        return scope in self._linkedin_granted_scopes_list()

    def _missing_linkedin_scopes(self, scopes):
        """Return the scopes of ``scopes`` this account was not granted.

        What a feature needs is declared as a list and answered as a list, so
        the modules that only report what is missing and the one that refuses
        to call read it the same way.

        :param scopes: the scopes the feature needs.
        :rtype: list
        """
        self.ensure_one()
        return [scope for scope in scopes if not self._has_linkedin_scope(scope)]

    def _check_linkedin_scopes(self, scopes):
        """Raise a readable error when a scope needed by a feature is missing.

        LinkedIn answers a bare ``403`` when a call needs a scope the token
        was not granted, which says nothing about what to do; the account has
        to be associated again once the product is enabled.

        :param scopes: the scopes the feature about to be called needs.
        """
        self.ensure_one()
        missing = self._missing_linkedin_scopes(scopes)
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
            endpoint=_ENDPOINT_POSTS_LINKEDIN,
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

    def _get_posts_gone(self, urns):
        """Ask LinkedIn which of these URNs it no longer serves.

        ``BATCH_GET`` answers ``results`` with the publications it served and
        ``errors`` with one entry per URN it refused, each carrying its own
        status. That per-URN status is the whole point: a ``404`` is a
        deletion, a ``403`` is a page role the token lost and a ``429`` is a
        throttled application, and the three arrive in the same answer.

        Fail open, like every other check of this kind: a request that could
        not be made confirms nothing, so the caller marks nothing. Which is
        why the answer is not read with :meth:`_get_posts`, that drops the
        ``errors`` block and raises as soon as the answer is not a ``200``.

        :param urns: the remote references to ask about, at most
            ``_BATCH_GET_MAX_IDS_LINKEDIN`` of them.
        :return: the URNs LinkedIn reported as gone.
        :rtype: set
        """
        self.ensure_one()
        urns = list(urns)
        if not urns:
            return set()
        try:
            response = self._request_linkedin(
                endpoint=_ENDPOINT_POSTS_LINKEDIN,
                headers=self.media_id._get_linkedin_headers(
                    self.sudo().access_token, x_restli_method="BATCH_GET"
                ),
                params_fields=["ids"],
                params_values={"ids": urns},
                return_json=False,
            )
        except Exception:  # noqa: BLE001 - unreachable is not deleted
            _logger.exception(
                "Error asking LinkedIn about %s publications, none of them is "
                "marked as gone",
                len(urns),
            )
            return set()
        if response.status_code != 200:
            _logger.warning(
                "LinkedIn answered %(code)s when asked about %(count)s "
                "publications, none of them is marked as gone: %(error)s",
                {
                    "code": response.status_code,
                    "count": len(urns),
                    "error": self._linkedin_error_message(response),
                },
            )
            return set()
        try:
            errors = response.json().get("errors") or {}
        except ValueError:
            _logger.warning(
                "LinkedIn answered something other than JSON when asked about "
                "%s publications, none of them is marked as gone",
                len(urns),
            )
            return set()
        return {
            urn
            for urn, error in errors.items()
            if isinstance(error, dict) and error.get("status") == 404
        }

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
        if not image_urns:
            return {}
        headers = self.media_id._get_linkedin_headers(
            self.sudo().access_token, x_restli_method="BATCH_GET"
        )
        download_urls = {}
        for batch in split_every(_BATCH_GET_MAX_IDS_LINKEDIN, image_urns, list):
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

    def _notify_statistics_failure(self, error):
        """Tell the user why the statistics of this account were not read.

        Serves the daily series of the page and, where
        ``social_media_linkedin_sync`` is installed, the import of the
        publications too: both write figures and both are wrapped in
        :meth:`~._statistics_guard`.

        The channel is not fixed: the sweep of the cron reaches this from the
        web client, but so does an association, which fills the series right
        after linking the account and answers with a redirect. That is what
        ``_notify_user()`` decides.

        :param error: whatever was raised while reading the account.
        """
        self.ensure_one()
        _logger.exception(
            "Error updating the statistics of the LinkedIn account %s",
            self.name,
        )
        self._notify_user(
            notif_type="social_kanban_danger",
            notif_message=self._linkedin_error_message(error),
            media="linkedin",
            account_name=self.name,
        )

    @contextmanager
    def _statistics_guard(self):
        """Isolate the statistics of one account in its own savepoint.

        The sweep writes one row per day and account, so an account LinkedIn
        refuses --a ``403`` on a page whose role was lost is the ordinary
        case-- must not roll back the rows already written for the others,
        nor stop the ones still to read. Each account is rolled back on its
        own and its responsible user is told why.

        ``social_media_linkedin_sync`` reuses it for the import, where what
        it protects is wider: reading a feed writes on the way, and the
        publications gone from LinkedIn are marked as deleted before their
        statistics are even asked for.

        What isolates the account is the guard of the base, ``_account_guard``.
        What this one adds is the answer to the failure: the responsible user
        is told instead of the log getting a line nobody reads.
        """
        with self._account_guard(on_error=self._notify_statistics_failure):
            yield

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
            fields.Date.subtract(date_to, months=_STATISTICS_HISTORY_MONTHS_LINKEDIN),
            date_to,
        )

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
        return self._linkedin_snapshot_accounts(*self._linkedin_refresh_window())

    def _linkedin_snapshot_accounts(self, date_from, date_to):
        """Ask the finder for the daily buckets of these accounts and write them.

        Each account goes in its own savepoint. A ``403`` on one of them is
        told to the user and the sweep carries on, so the rows already written
        for the other accounts stay written, and the account that failed is
        simply absent from the answer.

        :param date_from: first day to ask for, included.
        :param date_to: last day to ask for, included.
        :return: the buckets read, keyed by account id.
        :rtype: dict
        """
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
        linkedin._linkedin_snapshot_accounts(date_from, date_to)
        return super(SocialAccount, self - linkedin)._snapshot_statistics(
            date_from, date_to
        )

    def _linkedin_statistics_backfilled(self):
        """Tell whether the daily series of this account was already filled.

        The refresh only ever writes the days of
        :meth:`~._linkedin_refresh_window`, so a row older than that window
        can only have been written by a backfill that already ran. The series
        is therefore its own answer, and no field of the account has to be
        kept in step with it.

        Read with ``sudo()``, like the rows are written: they mirror what
        LinkedIn reported and belong to the responsible user of the account,
        and a manager asking for the history of somebody else's account has
        to get the same answer.

        :rtype: bool
        """
        self.ensure_one()
        return bool(
            self.env["social.account.statistics"]
            .sudo()
            .search_count(
                [
                    ("account_id", "=", self.id),
                    ("date", "<", self._linkedin_refresh_window()[0]),
                ],
                limit=1,
            )
        )

    def _backfill_statistics(self, force=False):
        """Fill the daily series of these accounts as far back as LinkedIn goes.

        The whole period costs a fixed number of calls -- the width of the
        window decides them and not the history of the page -- which is why
        base asks for it the moment an account is linked.

        An account that already has the series is skipped: the refresh only
        ever writes the last days, so a row older than its window can only
        come from a backfill that already ran. That makes the second call, the
        one the initial synchronization of ``social_media_sync`` makes, the
        retry of an association whose history could not be read rather than a
        repetition of it.

        :param force: ask LinkedIn for the period again even if the series is
            already there, which is what the button of the account form
            passes.
        :return: whatever the other connectors answer for their own accounts.
        """
        linkedin = self.filtered(lambda account: account.media_type == "linkedin")
        pending = (
            linkedin
            if force
            else linkedin.filtered(
                lambda account: not account._linkedin_statistics_backfilled()
            )
        )
        if pending:
            pending._snapshot_statistics(*pending._linkedin_backfill_window())
        return super(SocialAccount, self - linkedin)._backfill_statistics(force=force)

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
        start_time = datetime.combine(start, datetime.min.time())
        end_time = datetime.combine(end + timedelta(days=1), datetime.min.time())
        return epoch_milliseconds(start_time), epoch_milliseconds(end_time)

    def _linkedin_statistics_chunks(self, date_from, date_to):
        """Split a range of days into the calls the finder can answer.

        The endpoint answers at most ``_STATISTICS_MAX_BUCKETS_LINKEDIN``
        buckets and documents that it does not support pagination, so what is
        split is the range and not the response: a wider period becomes
        several calls, each one asking for the days the finder serves at once.

        The chunks are contiguous and both ends of every one are included, so
        together they cover the whole range without leaving a gap or asking
        for a day twice.

        :param date_from: first day of the range, included.
        :param date_to: last day of the range, included.
        :return: one ``(first_day, last_day)`` pair per call, both included.
        :rtype: list
        """
        self.ensure_one()
        first = fields.Date.to_date(date_from)
        last = fields.Date.to_date(date_to)
        if not (first and last) or first > last:
            return []
        chunks = []
        while first <= last:
            chunk_to = min(
                first + timedelta(days=_STATISTICS_MAX_BUCKETS_LINKEDIN - 1), last
            )
            chunks.append((first, chunk_to))
            first = chunk_to + timedelta(days=1)
        return chunks

    def _snapshot_linkedin_statistics(self, date_from, date_to):
        """Write the rows of one account for the given range of days.

        The range is asked for in as many calls as it takes and the buckets of
        every one are merged before writing, so the series is written once for
        the whole period. A chunk LinkedIn answers short simply contributes
        the days it did report: the ones missing leave no row, exactly as they
        do within a single call.

        The buckets are given back as they were read, keyed by the ISO day and
        with the tuple ``_get_linkedin_daily_statistics`` builds, so the caller
        of a sweep can compare them without asking the finder a second time.

        :param date_from: first day to write, included.
        :param date_to: last day to write, included.
        :return: the buckets read, keyed by ISO day.
        :rtype: dict
        """
        self.ensure_one()
        buckets = {}
        for chunk_from, chunk_to in self._linkedin_statistics_chunks(
            date_from, date_to
        ):
            start_time, end_time = self._linkedin_statistics_interval(
                chunk_from, chunk_to
            )
            buckets.update(
                self._get_linkedin_daily_statistics(start_time, end_time, "DAY")
            )
        self._write_statistics_rows(
            {
                day: self._linkedin_statistics_values(figures)
                for day, figures in buckets.items()
            }
        )
        return buckets

    @api.model
    def _linkedin_statistics_values(self, figures):
        """Return one tuple of figures as the statistics fields that hold it.

        Shared by the two halves, and that is why it lives here: the daily
        sweep of the page maps a bucket with it, and the import of
        ``social_media_linkedin_sync`` maps the figures of a publication.
        Both tuples carry the same six figures in the same order, so a second
        copy of this mapping is what would let the daily series and the
        imported publications stop speaking the same language.

        :param figures: the six figures --clicks, likes, comments, shares,
            engagement and impressions-- as ``_get_linkedin_daily_statistics``
            builds them for a day and ``_parse_share_statistics`` for a
            publication. Empty when LinkedIn reported none.
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

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures LinkedIn reports for these publications.

        Nothing here walks the feed: Odoo already knows the URN of every
        publication it is handed, so at most three calls answer a whole page of
        them however much the page has published --and only one when every URN
        of the page is a share, which is what this connector publishes. That is
        what lets it keep the figures of a publication up to date with no
        synchronization module installed.

        Each account goes in its own savepoint, and its responsible user is
        told when LinkedIn refuses it: the pass writes as it goes, so what was
        already written for the accounts before must stay written. An account
        without an organization cannot even be asked, since the finder is
        addressed by organization.

        :param post_accounts: the lines to read, every one with a
            ``remote_ref``.
        :return: the lines LinkedIn answered for, plus whatever the other
            connectors answered for their own.
        """
        linkedin = post_accounts.filtered(
            lambda line: line.account_id.media_type == "linkedin"
        )
        refreshed = super()._refresh_post_statistics(post_accounts - linkedin)
        for account, lines in linkedin.grouped("account_id").items():
            if not account.linkedin_account_id:
                continue
            with account._statistics_guard():
                refreshed |= account._linkedin_write_post_statistics(lines)
        return refreshed

    def _linkedin_write_post_statistics(self, post_accounts):
        """Ask LinkedIn for these publications and write what it answers.

        A URN missing from the answer is a publication nobody interacted with
        and not a publication that could not be read:
        ``organizationalEntityShareStatistics`` leaves out the entities with no
        activity at all, so its silence about one of them is a figure of zero.
        Which is why the whole batch either answers -- and every line of it is
        written, with the date it was read on -- or raises, and the guard above
        rolls the account back.

        The lines are written with ``sudo()`` for the same reason the daily
        series is: they mirror what LinkedIn reported and belong to the
        responsible of the account, and the *Update* button of a regular user
        has to work all the same.

        :param post_accounts: the lines of this account to read.
        :return: those same lines.
        :rtype: recordset
        """
        self.ensure_one()
        figures = self._get_entity_statistics(
            posts=[{"id": urn} for urn in post_accounts.mapped("remote_ref")]
        )
        read_on = fields.Datetime.now()
        for line in post_accounts:
            line.sudo().write(
                {
                    **self._linkedin_statistics_values(figures.get(line.remote_ref)),
                    "statistics_date": read_on,
                }
            )
        return post_accounts

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
        for batch in _batch_urns_by_url_size(
            urns,
            param_field,
            params_fields=params_fields,
            params_values=params_values,
        ):
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
        urns = self._filter_urns(posts, _URN_UGC_POST_LINKEDIN)
        for batch in _batch_urns_by_url_size(
            urns,
            "ids",
            params_fields=params_fields,
            params_values=params_values,
        ):
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
        # The same endpoint asked once per kind of publication. Both bring the
        # clicks, the shares, the engagement and the impressions; the likes and
        # the comments come from ``socialActions`` below, which is the source
        # LinkedIn documents as the up-to-date one.
        errors_by_field = {
            "shares": _("The statistics of the shared publications could not be read"),
            "ugcPosts": _("The statistics of the publications could not be read"),
        }
        data = {}
        for urn_prefix, param_field, urn_key in _ENTITY_STATISTICS_LINKEDIN:
            data.update(
                self._get_entity_share_statistics(
                    self._filter_urns(posts, urn_prefix),
                    param_field,
                    urn_key,
                    errors_by_field[param_field],
                    **entity_params,
                )
            )
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
                "count": _STATISTICS_MAX_BUCKETS_LINKEDIN,
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
            day = datetime_from_epoch_milliseconds(bucket_start).date().isoformat()
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

    def _linkedin_check_updates(self, buckets_by_account):
        """Announce the accounts whose figures moved since the last import.

        Empty on purpose: without a module able to import the publications
        there is nothing to compare against and nothing to announce.

        A hook of this connector and not of ``social_media_base``: base is not
        designed against a single real case, and X will declare its own.

        :param buckets_by_account: ``{account.id: buckets}`` as
            ``_linkedin_refresh_statistics`` returns them, that is, the SIX raw
            figures per day. Trimming to the five watched ones is the callee's
            job, never this argument's.
        :return: whether any account was flagged, to be OR-ed into the cron
            result.
        :rtype: bool
        """
        return False

    def _run_check_media_updates(self):
        """Renew the credentials and rewrite the last days of the time series.

        One call per account, whatever the number of publications: the daily
        figures the finder answers are those of the whole page, so the URNs of
        the publications never enter the query.

        What is read here is offered to ``_linkedin_check_updates``, which is
        empty in this module. A module able to import the publications answers
        it and compares the page against the mark the last import left; on its
        own the connector only writes the series the graph view reads.

        The answer of the previous connectors is not looked at. Each one
        checks its own accounts, so a connector that found updates does not
        silence the others.

        :return: whether new updates were found, by this connector or before.
        :rtype: bool
        """
        update = super()._run_check_media_updates()
        try:
            # Which accounts this cron may walk at all is base's to answer,
            # through ``_get_check_media_updates_domain``: a module that also
            # reads the social media has reasons to leave one out for a while
            # ---an account whose first import has not run yet, say--- and
            # those reasons are never this connector's to spell out. What is
            # added here is the connector's own: its media type, and having an
            # organization, because the feed of an account without one cannot
            # even be asked for. ``sudo`` because the cron record sets no user
            # and the accounts belong to every responsible.
            #
            # The time series is written for every account that can be
            # asked, ``need_update`` or not: the flag says the user has an
            # import pending, not that the figures of the page stopped
            # moving. ``_linkedin_refresh_statistics`` isolates each account
            # on its own, so one that answers an error does not stop the rest.
            #
            # Announcing what moved is not this module's: without something
            # able to import the publications there is nothing to compare a
            # page against. ``_linkedin_check_updates`` is the empty hook that
            # says it, and the buckets travel to it as an argument so the
            # finder is never asked twice for the same days.
            accounts = self.sudo().search(
                self._get_check_media_updates_domain()
                + [
                    ("media_type", "=", "linkedin"),
                    ("linkedin_account_id", "!=", False),
                ]
            )
            buckets_by_account = accounts._linkedin_refresh_statistics()
            update = accounts._linkedin_check_updates(buckets_by_account) or update
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
