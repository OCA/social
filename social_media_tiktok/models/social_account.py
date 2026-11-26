# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import time
from datetime import timedelta
from urllib.parse import urljoin

import requests

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_tiktok_utils import _URL_OAUTH2_TOKEN_TIKTOK, _URL_TIKTOK_API

_logger = logging.getLogger(__name__)

# Direct Post uploads the file in chunks between 5 MB and 64 MB; a chunk of
# 10 MB keeps the number of requests low for the usual phone video.
_MAX_CHUNK_SIZE_TIKTOK = 10 * 1024 * 1024
# TikTok processes the file asynchronously, so the publication is read back
# until it is published. The wait is bounded so a stuck upload does not pin
# the worker forever.
_PUBLISH_POLL_ATTEMPTS_TIKTOK = 30
_PUBLISH_POLL_DELAY_TIKTOK = 2
_ALLOWED_VIDEO_MIMETYPES_TIKTOK = ("video/mp4", "video/quicktime", "video/webm")
# The video query accepts up to 20 identifiers per call.
_VIDEO_QUERY_BATCH_TIKTOK = 20


class SocialAccount(models.Model):
    """TikTok implementation of the social account API calls."""

    _inherit = "social.account"

    tiktok_access_token = fields.Char(groups="base.group_system")
    tiktok_refresh_token = fields.Char(groups="base.group_system")
    tiktok_token_expiration_date = fields.Datetime(groups="base.group_system")
    tiktok_open_id = fields.Char(groups="base.group_system")
    tiktok_client_key = fields.Char(
        string="TikTok Client Key", groups="base.group_system"
    )
    tiktok_client_secret = fields.Char(groups="base.group_system")
    tiktok_account_type = fields.Char()
    tiktok_username = fields.Char()
    tiktok_avatar_url = fields.Char()
    following_count = fields.Integer(default=0)
    likes_count = fields.Integer(default=0)
    video_count = fields.Integer(default=0)

    def _get_tiktok_headers(self):
        return {
            "Authorization": f"Bearer {self._refresh_tiktok_token()}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def _fields_account_url(self):
        urls = super()._fields_account_url()
        if self.media_type == "tiktok" and self.tiktok_username:
            urls["tiktok"] = f"https://www.tiktok.com/@{self.tiktok_username}"
        return urls

    def _get_removal_values(self):
        res = super()._get_removal_values()
        res.update(
            {
                "tiktok_access_token": False,
                "tiktok_refresh_token": False,
                "tiktok_token_expiration_date": False,
                "tiktok_open_id": False,
                "tiktok_client_key": False,
                "tiktok_client_secret": False,
            }
        )
        return res

    def _get_tiktok_oauth_wizard(self, state):
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
                order="id desc",
            )
        )

    def _consume_tiktok_oauth_wizard(self, state):
        """Drop the wizard of this OAuth flow so its state cannot be replayed."""
        self._get_tiktok_oauth_wizard(state).unlink()

    def get_access_token_tiktok(self, authorization_code, state):
        """Exchange the OAuth2 authorization code for an access token.

        :return: The client key, the client secret and the token response.
        :rtype: tuple
        """
        wizard_social_account = self._get_tiktok_oauth_wizard(state)
        if not wizard_social_account:
            raise UserError(
                self.env._(
                    "Invalid OAuth state token. Please restart the "
                    "account association process."
                )
            )
        client_key = wizard_social_account.tiktok_client_key
        client_secret = wizard_social_account.tiktok_client_secret
        response = requests.post(
            _URL_OAUTH2_TOKEN_TIKTOK,
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self._tiktok_redirect_uri(),
                "code_verifier": wizard_social_account.tiktok_code_verifier,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "TikTok token exchange failed: %(error)s", error=response.text
                )
            )
        return client_key, client_secret, response.json()

    def create_account_tiktok(self, client_key, client_secret, tokens):
        """Create or update the account of the authorized TikTok user."""
        access_token = tokens.get("access_token")
        open_id = tokens.get("open_id")
        if not access_token or not open_id:
            raise UserError(self.env._("TikTok returned no access token."))
        user_info = self._get_tiktok_user_info(access_token)
        existing = self._find_account_to_associate(
            "tiktok", open_id, username=user_info.get("username")
        )
        if existing:
            existing._check_can_associate()
        values = {
            "remote_ref": open_id,
            "name": user_info.get("display_name")
            or user_info.get("username")
            or "TikTok",
            "username": user_info.get("username"),
            "tiktok_username": user_info.get("username"),
            "media_id": self.env.ref("social_media_tiktok.social_media_tiktok").id,
            "tiktok_client_key": client_key,
            "tiktok_client_secret": client_secret,
            "tiktok_access_token": access_token,
            "tiktok_refresh_token": tokens.get("refresh_token"),
            "tiktok_token_expiration_date": fields.Datetime.now()
            + timedelta(seconds=tokens.get("expires_in", 86400)),
            "tiktok_open_id": open_id,
            "tiktok_account_type": user_info.get("account_type"),
            "tiktok_avatar_url": user_info.get("avatar_url"),
            "follower_count": user_info.get("follower_count", 0),
            "following_count": user_info.get("following_count", 0),
            "likes_count": user_info.get("likes_count", 0),
            "video_count": user_info.get("video_count", 0),
        }
        if existing:
            if not existing.active:
                values["active"] = True
            existing.sudo().write(values)
        else:
            self.sudo().create(dict(values, user_id=self.env.user.id))
        self._trigger_initial_sync()

    def _get_tiktok_user_info(self, access_token=None):
        token = access_token or self._refresh_tiktok_token()
        fields = (
            "open_id,union_id,avatar_url,display_name,username,"
            "follower_count,following_count,likes_count,video_count"
        )
        response = requests.get(
            _URL_TIKTOK_API + "user/info/",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": fields},
            timeout=30,
        )
        if response.status_code != 200:
            _logger.error("Error reading the TikTok user: %s", response.text)
            return {}
        return response.json().get("data", {}).get("user", {})

    def _tiktok_redirect_uri(self):
        """Return the OAuth callback URL, the same on both sides of the flow."""
        return urljoin(self.get_base_url(), "/social_tiktok/callback")

    def _refresh_tiktok_token(self):
        """Return a valid access token, refreshing it when it has expired."""
        self.ensure_one()
        if (
            self.sudo().tiktok_token_expiration_date
            and self.sudo().tiktok_token_expiration_date > fields.Datetime.now()
        ):
            return self.sudo().tiktok_access_token
        if not self.sudo().tiktok_refresh_token:
            raise SocialCredentialsError(
                "TikTok token expired and the account has no refresh token: "
                "authorize it again."
            )
        response = requests.post(
            _URL_OAUTH2_TOKEN_TIKTOK,
            data={
                "client_key": self.sudo().tiktok_client_key,
                "client_secret": self.sudo().tiktok_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.sudo().tiktok_refresh_token,
            },
            timeout=30,
        )
        if response.status_code in (400, 401, 403):
            raise SocialCredentialsError(
                f"TikTok refused the credentials ({response.status_code}): "
                f"{response.text}"
            )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "TikTok token refresh failed: %(error)s", error=response.text
                )
            )
        data = response.json()
        self.sudo().write(
            {
                "tiktok_access_token": data.get("access_token"),
                "tiktok_refresh_token": data.get("refresh_token")
                or self.sudo().tiktok_refresh_token,
                "tiktok_token_expiration_date": fields.Datetime.now()
                + timedelta(seconds=data.get("expires_in", 86400)),
            }
        )
        return data.get("access_token")

    def validate_access_token(self):
        """Renew the TikTok token when its dates say it has expired."""
        res = super().validate_access_token()
        if self.media_type == "tiktok":
            self._refresh_tiktok_token()
        return res

    def _refresh_credentials(self):
        if self.media_type != "tiktok":
            return super()._refresh_credentials()
        try:
            return bool(self._refresh_tiktok_token())
        except (UserError, SocialCredentialsError) as error:
            _logger.warning("TikTok credentials could not be renewed: %s", error)
            return False

    def _update_account_data(self):
        if self.media_type != "tiktok":
            return super()._update_account_data()
        user_info = self._get_tiktok_user_info()
        if not user_info:
            return
        values = {
            "name": user_info.get("display_name") or user_info.get("username"),
            "username": user_info.get("username"),
            "tiktok_username": user_info.get("username"),
            "tiktok_account_type": user_info.get("account_type"),
            "tiktok_avatar_url": user_info.get("avatar_url"),
        }
        if user_info.get("avatar_url"):
            media_content = requests.get(user_info["avatar_url"], timeout=10)
            if media_content.status_code == 200:
                values["image_1920"] = base64.b64encode(media_content.content)
        self.write(values)

    def _tiktok_post_info(self, title, privacy_level="SELF_ONLY"):
        return {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        }

    def _post_tiktok_video(self, post_account):
        """Upload and publish the video of the post through Direct Post.

        The Content Posting API works in three steps: the upload is
        initialized, which answers the identifier of the publication and the
        URL to send the file to; the file is uploaded; and the publication is
        read back from its status until TikTok has processed it, because only
        then it answers the identifier of the video.
        """
        videos = post_account.post_id.video_ids
        if not videos:
            raise UserError(self.env._("TikTok posts require a video."))
        title = (post_account.message or post_account.post_id.display_name)[:150]
        video_bytes = videos[0].raw
        total = len(video_bytes)
        chunk_size = min(total, _MAX_CHUNK_SIZE_TIKTOK)
        # TikTok splits the file in chunks of exactly ``chunk_size`` and lets
        # the last one absorb the remainder (up to 128 MB), so the count is
        # ``floor`` and not ``ceil``: a remainder below the 5 MB minimum is
        # only valid on the final chunk.
        total_chunks = max(total // chunk_size, 1)
        video_mimetype = videos[0].mimetype or "video/mp4"
        if video_mimetype not in _ALLOWED_VIDEO_MIMETYPES_TIKTOK:
            video_mimetype = "video/mp4"
        # 1. Initialize the upload and get the URL to send the file to.
        initiate = requests.post(
            _URL_TIKTOK_API + "post/publish/video/init/",
            headers=self._get_tiktok_headers(),
            json={
                "post_info": self._tiktok_post_info(title),
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": total,
                    "chunk_size": chunk_size,
                    "total_chunk_count": total_chunks,
                },
            },
            timeout=60,
        )
        if initiate.status_code in (401, 403):
            try:
                error = initiate.json().get("error", {})
            except ValueError:
                error = {}
            if initiate.status_code == 401 or error.get("code") in (
                "access_token_invalid",
                "invalid_access_token",
                "scope_not_authorized",
            ):
                raise SocialCredentialsError(
                    f"TikTok refused the credentials ({initiate.status_code}): "
                    f"{initiate.text}"
                )
            raise UserError(
                self.env._(
                    "TikTok refused the publication: %(error)s",
                    error=initiate.text,
                )
            )
        if initiate.status_code != 200:
            raise UserError(
                self.env._(
                    "TikTok upload initiation failed: %(error)s", error=initiate.text
                )
            )
        data = initiate.json().get("data", {})
        publish_id = data.get("publish_id")
        upload_url = data.get("upload_url")
        if not publish_id or not upload_url:
            raise UserError(
                self.env._("TikTok upload initiation returned no upload URL.")
            )
        # 2. Upload the file, in as many chunks as the initialization asked.
        for index in range(total_chunks):
            start = index * chunk_size
            end = total - 1 if index == total_chunks - 1 else start + chunk_size - 1
            upload = requests.put(
                upload_url,
                headers={
                    "Content-Type": video_mimetype,
                    "Content-Range": f"bytes {start}-{end}/{total}",
                },
                data=video_bytes[start : end + 1],
                timeout=300,
            )
            if upload.status_code not in (200, 201, 206):
                raise UserError(
                    self.env._(
                        "TikTok video upload failed: %(error)s", error=upload.text
                    )
                )
        # 3. Wait until TikTok publishes the video and read its identifier.
        return self._wait_for_tiktok_publication(publish_id)

    def _wait_for_tiktok_publication(self, publish_id):
        """Return the identifier of the video a publication ends up with.

        Direct Post only answers the identifier of the publication once
        TikTok has processed the file, so the status is read until it is
        published. The identifier is only returned for a public publication:
        an unaudited app publishes privately and gets no reference back, and
        the caller must not invent one from the ``publish_id``.

        :param publish_id: the identifier answered when initializing the upload.
        :rtype: str | bool
        """
        for _attempt in range(_PUBLISH_POLL_ATTEMPTS_TIKTOK):
            response = requests.post(
                _URL_TIKTOK_API + "post/publish/status/fetch/",
                headers=self._get_tiktok_headers(),
                json={"publish_id": publish_id},
                timeout=60,
            )
            if response.status_code in (401, 403):
                raise SocialCredentialsError(
                    f"TikTok refused the credentials ({response.status_code}): "
                    f"{response.text}"
                )
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "TikTok could not read the status of the publication: "
                        "%(error)s",
                        error=response.text,
                    )
                )
            data = response.json().get("data", {})
            status = data.get("status")
            if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                video_ids = data.get("publicaly_available_post_id") or []
                # A private publication carries no video identifier: TikTok
                # only returns it once the post is public and moderated.
                return str(video_ids[0]) if video_ids else False
            if status == "FAILED":
                raise UserError(
                    self.env._(
                        "TikTok failed to process the video: %(reason)s",
                        reason=data.get("fail_reason") or status,
                    )
                )
            time.sleep(_PUBLISH_POLL_DELAY_TIKTOK)
        raise UserError(
            self.env._("TikTok did not finish processing the video in time.")
        )

    def _delete_tiktok_video(self, post_account):
        raise UserError(
            self.env._(
                "TikTok does not offer an API to delete a publication: delete "
                "it in the TikTok app and archive the publication here to keep "
                "its history."
            )
        )

    def _get_tiktok_videos(self, max_count=20):
        """Return the videos published by this TikTok account."""
        response = requests.post(
            _URL_TIKTOK_API + "video/list/",
            headers=self._get_tiktok_headers(),
            json={"max_count": max_count, "cursor": 0},
            timeout=60,
        )
        if response.status_code != 200:
            _logger.error("Error listing TikTok videos: %s", response.text)
            return []
        return response.json().get("data", {}).get("videos", [])

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures TikTok reports for these videos.

        :param post_accounts: the lines to read, every one with a ``remote_ref``.
        :rtype: recordset
        """
        tiktok = post_accounts.filtered(
            lambda line: line.account_id.media_type == "tiktok"
        )
        refreshed = super()._refresh_post_statistics(post_accounts - tiktok)
        if not tiktok:
            return refreshed
        return refreshed | self._tiktok_write_post_statistics(tiktok)

    def _tiktok_write_post_statistics(self, post_accounts):
        """Ask TikTok for these videos and write what it answers."""
        self.ensure_one()
        videos_by_id = {}
        for start in range(0, len(post_accounts), _VIDEO_QUERY_BATCH_TIKTOK):
            batch = post_accounts[start : start + _VIDEO_QUERY_BATCH_TIKTOK]
            response = requests.post(
                _URL_TIKTOK_API + "video/query/",
                headers=self._get_tiktok_headers(),
                params={"fields": "id,like_count,comment_count,share_count,view_count"},
                json={"filters": {"video_ids": batch.mapped("remote_ref")}},
                timeout=30,
            )
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "TikTok statistics failed: %(error)s", error=response.text
                    )
                )
            videos_by_id.update(
                {
                    str(video.get("id")): video
                    for video in response.json().get("data", {}).get("videos", [])
                }
            )
        read_on = fields.Datetime.now()
        for line in post_accounts:
            data = videos_by_id.get(str(line.remote_ref), {})
            line.sudo().write(
                {
                    "like_count": data.get("like_count", 0),
                    "comment_count": data.get("comment_count", 0),
                    "share_count": data.get("share_count", 0),
                    "impression_count": data.get("view_count", 0),
                    "statistics_date": read_on,
                }
            )
        return post_accounts
