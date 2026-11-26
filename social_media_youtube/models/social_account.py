# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta
from urllib.parse import urljoin

import requests

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_youtube_utils import _URL_GOOGLE_TOKEN, _URL_YOUTUBE_API

_logger = logging.getLogger(__name__)

# videos.list accepts at most 50 identifiers per call.
_VIDEO_LIST_BATCH_YOUTUBE = 50


class SocialAccount(models.Model):
    """YouTube implementation of the social account API calls."""

    _inherit = "social.account"

    youtube_channel_id = fields.Char(groups="base.group_system")
    youtube_access_token = fields.Char(groups="base.group_system")
    youtube_refresh_token = fields.Char(groups="base.group_system")
    youtube_token_expiration_date = fields.Datetime(groups="base.group_system")
    youtube_client_id = fields.Char(
        string="YouTube Client ID", groups="base.group_system"
    )
    youtube_client_secret = fields.Char(groups="base.group_system")

    def _youtube_redirect_uri(self):
        return urljoin(self.get_base_url(), "/social_youtube/callback")

    def _fields_account_url(self):
        urls = super()._fields_account_url()
        if self.sudo().youtube_channel_id:
            urls["youtube"] = (
                f"https://www.youtube.com/channel/{self.sudo().youtube_channel_id}"
            )
        return urls

    def _get_removal_values(self):
        res = super()._get_removal_values()
        res.update(
            {
                "youtube_access_token": False,
                "youtube_refresh_token": False,
                "youtube_token_expiration_date": False,
                "youtube_channel_id": False,
                "youtube_client_id": False,
                "youtube_client_secret": False,
            }
        )
        return res

    def _get_youtube_oauth_wizard(self, state):
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

    def _consume_youtube_oauth_wizard(self, state):
        self._get_youtube_oauth_wizard(state).unlink()

    def get_access_token_youtube(self, code, state):
        """Exchange the OAuth2 authorization code for tokens."""
        wizard_social_account = self._get_youtube_oauth_wizard(state)
        if not wizard_social_account:
            raise UserError(
                self.env._(
                    "Invalid OAuth state token. Please restart the "
                    "account association process."
                )
            )
        client_id = wizard_social_account.youtube_client_id
        client_secret = wizard_social_account.youtube_client_secret
        response = requests.post(
            _URL_GOOGLE_TOKEN,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._youtube_redirect_uri(),
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "YouTube token exchange failed: %(error)s", error=response.text
                )
            )
        return client_id, client_secret, response.json()

    def create_youtube_account(self, client_id, client_secret, tokens):
        """Create or update the account of the authorized YouTube channel."""
        access_token = tokens.get("access_token")
        if not access_token:
            raise UserError(self.env._("YouTube returned no access token."))
        channel = self._get_youtube_channel(access_token)
        channel_id = channel.get("id")
        if not channel_id:
            raise UserError(self.env._("Could not find any YouTube channel."))
        existing = self._find_account_to_associate(
            "youtube", channel_id, username=channel.get("title")
        )
        if existing:
            existing._check_can_associate()
        values = {
            "remote_ref": channel_id,
            "name": channel.get("title") or "YouTube",
            "username": channel.get("title"),
            "media_id": self.env.ref("social_media_youtube.social_media_youtube").id,
            "youtube_channel_id": channel_id,
            "youtube_access_token": access_token,
            "youtube_refresh_token": tokens.get("refresh_token"),
            "youtube_token_expiration_date": fields.Datetime.now()
            + timedelta(seconds=tokens.get("expires_in", 3600)),
            "youtube_client_id": client_id,
            "youtube_client_secret": client_secret,
        }
        if existing:
            if not existing.active:
                values["active"] = True
            existing.sudo().write(values)
        else:
            self.sudo().create(dict(values, user_id=self.env.user.id))
        self._trigger_initial_sync()

    def _get_youtube_channel(self, access_token=None):
        token = access_token or self._refresh_youtube_token()
        response = requests.get(
            f"{_URL_YOUTUBE_API}/youtube/v3/channels",
            params={"part": "snippet,statistics", "mine": "true"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if response.status_code != 200:
            _logger.error("Error reading the YouTube channel: %s", response.text)
            return {}
        items = response.json().get("items", [])
        return items[0] if items else {}

    def _refresh_youtube_token(self):
        """Return a valid access token, refreshing it when it has expired."""
        self.ensure_one()
        if (
            self.sudo().youtube_token_expiration_date
            and self.sudo().youtube_token_expiration_date > fields.Datetime.now()
        ):
            return self.sudo().youtube_access_token
        if not self.sudo().youtube_refresh_token:
            raise SocialCredentialsError(
                "YouTube token expired and the account has no refresh token: "
                "authorize it again."
            )
        response = requests.post(
            _URL_GOOGLE_TOKEN,
            data={
                "client_id": self.sudo().youtube_client_id,
                "client_secret": self.sudo().youtube_client_secret,
                "refresh_token": self.sudo().youtube_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code in (400, 401, 403):
            raise SocialCredentialsError(
                f"YouTube refused the credentials ({response.status_code}): "
                f"{response.text}"
            )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "YouTube token refresh failed: %(error)s", error=response.text
                )
            )
        data = response.json()
        self.sudo().write(
            {
                "youtube_access_token": data.get("access_token"),
                "youtube_token_expiration_date": fields.Datetime.now()
                + timedelta(seconds=data.get("expires_in", 3600)),
            }
        )
        return data.get("access_token")

    def validate_access_token(self):
        """Renew the YouTube token when its dates say it has expired."""
        res = super().validate_access_token()
        if self.media_type == "youtube":
            self._refresh_youtube_token()
        return res

    def _refresh_credentials(self):
        if self.media_type != "youtube":
            return super()._refresh_credentials()
        try:
            return bool(self._refresh_youtube_token())
        except (UserError, SocialCredentialsError) as error:
            _logger.warning("YouTube credentials could not be renewed: %s", error)
            return False

    def _update_account_data(self):
        if self.media_type != "youtube":
            return super()._update_account_data()
        channel = self._get_youtube_channel()
        if channel:
            statistics = channel.get("statistics", {})
            self.write(
                {
                    "name": channel.get("title") or "YouTube",
                    "username": channel.get("title"),
                    "follower_count": int(statistics.get("subscriberCount") or 0),
                }
            )

    def _post_youtube_video(self, post_account):
        """Upload a video to YouTube using a resumable upload."""
        videos = post_account.post_id.video_ids
        if not videos:
            raise UserError(self.env._("YouTube posts require a video."))
        video = videos[0]
        access_token = self._refresh_youtube_token()
        video_bytes = video.raw
        content_type = video.mimetype or "video/mp4"
        title = (post_account.message or post_account.post_id.display_name)[:100]
        # YouTube rejects angle brackets in the title and the description.
        title = title.replace("<", "").replace(">", "")
        privacy_status = post_account.post_id.youtube_privacy_status or "private"

        initiate = requests.post(
            f"{_URL_YOUTUBE_API}/upload/youtube/v3/videos"
            "?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": content_type,
                "X-Upload-Content-Length": str(len(video_bytes)),
            },
            json={
                "snippet": {
                    "title": title,
                    "description": post_account.message or "",
                },
                "status": {"privacyStatus": privacy_status},
            },
            timeout=30,
        )
        if initiate.status_code in (401, 403):
            raise SocialCredentialsError(
                f"YouTube refused the credentials ({initiate.status_code}): "
                f"{initiate.text}"
            )
        upload_url = initiate.headers.get("Location")
        if not upload_url:
            raise UserError(
                self.env._(
                    "YouTube upload initiation failed: %(error)s",
                    error=initiate.text,
                )
            )
        upload = requests.put(
            upload_url,
            data=video_bytes,
            headers={"Content-Type": content_type},
            timeout=600,
        )
        if upload.status_code not in (200, 201):
            raise UserError(
                self.env._("YouTube video upload failed: %(error)s", error=upload.text)
            )
        return upload.json().get("id")

    def _delete_youtube_video(self, post_account):
        if not post_account.remote_ref:
            return {"success": True, "message": ""}
        access_token = self._refresh_youtube_token()
        response = requests.delete(
            f"{_URL_YOUTUBE_API}/youtube/v3/videos",
            params={"id": post_account.remote_ref},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if response.status_code not in (200, 204):
            raise UserError(
                self.env._(
                    "YouTube video deletion failed: %(error)s", error=response.text
                )
            )
        return {"success": True, "message": ""}

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures YouTube reports for these videos.

        :param post_accounts: the lines to read, every one with a ``remote_ref``.
        :rtype: recordset
        """
        youtube = post_accounts.filtered(
            lambda line: line.account_id.media_type == "youtube"
        )
        refreshed = super()._refresh_post_statistics(post_accounts - youtube)
        if not youtube:
            return refreshed
        return refreshed | self._youtube_write_post_statistics(youtube)

    def _youtube_write_post_statistics(self, post_accounts):
        """Ask YouTube for these videos and write what it answers.

        The Data API reports the counters as strings, so each one is cast
        before it reaches an integer field. ``videos.list`` takes at most 50
        identifiers per call, so the batch is split.
        """
        self.ensure_one()
        access_token = self._refresh_youtube_token()
        statistics_by_id = {}
        for start in range(0, len(post_accounts), _VIDEO_LIST_BATCH_YOUTUBE):
            batch = post_accounts[start : start + _VIDEO_LIST_BATCH_YOUTUBE]
            response = requests.get(
                f"{_URL_YOUTUBE_API}/youtube/v3/videos",
                params={
                    "part": "statistics",
                    "id": ",".join(batch.mapped("remote_ref")),
                },
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "YouTube statistics failed: %(error)s", error=response.text
                    )
                )
            statistics_by_id.update(
                {
                    item.get("id"): item.get("statistics", {})
                    for item in response.json().get("items", [])
                }
            )
        read_on = fields.Datetime.now()
        for line in post_accounts:
            data = statistics_by_id.get(line.remote_ref, {})
            line.sudo().write(
                {
                    "like_count": int(data.get("likeCount", 0)),
                    "comment_count": int(data.get("commentCount", 0)),
                    "impression_count": int(data.get("viewCount", 0)),
                    "statistics_date": read_on,
                }
            )
        return post_accounts
