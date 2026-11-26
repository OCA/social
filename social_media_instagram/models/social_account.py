# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import time
from datetime import timedelta, timezone
from urllib.parse import urljoin

import requests
from dateutil import parser as date_parser

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_instagram_utils import (
    _GRAPH_VERSION,
    _URL_GRAPH,
    _URL_TOKEN_INSTAGRAM,
)

_logger = logging.getLogger(__name__)

_STATUS_CONTAINER_ERROR = ("ERROR", "EXPIRED")
_STATUS_CONTAINER_POLL_ATTEMPTS = 30
_STATUS_CONTAINER_POLL_DELAY = 2
_IMPORT_BATCH_SIZE = 50
_IMPORT_MAX_PAGES = 5
# A long-lived token is renewed by asking Instagram while it is still valid,
# so the renewal has to happen ahead of its date: once it has passed, only the
# user can authorize the account again.
_TOKEN_MARGIN_DAYS_INSTAGRAM = 7
_MAX_CAPTION_LENGTH_INSTAGRAM = 2200
_MAX_IMAGES_INSTAGRAM = 10
_MAX_IMAGE_SIZE_INSTAGRAM = 8 * 1024 * 1024


class SocialAccount(models.Model):
    """Instagram implementation of the social account API calls."""

    _inherit = "social.account"

    instagram_account_id = fields.Char(groups="base.group_system")
    instagram_access_token = fields.Char(groups="base.group_system")
    instagram_app_id = fields.Char(
        string="Instagram App ID", groups="base.group_system"
    )
    instagram_app_secret = fields.Char(groups="base.group_system")

    def _instagram_redirect_uri(self):
        return urljoin(self.get_base_url(), "/social_instagram/callback")

    def _fields_account_url(self):
        urls = super()._fields_account_url()
        if self.media_type == "instagram" and self.username:
            urls["instagram"] = f"https://www.instagram.com/{self.username}"
        return urls

    def _get_removal_values(self):
        res = super()._get_removal_values()
        res.update(
            {
                "instagram_access_token": False,
                "instagram_account_id": False,
                "instagram_app_id": False,
                "instagram_app_secret": False,
            }
        )
        return res

    def _get_instagram_oauth_wizard(self, state):
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

    def _consume_instagram_oauth_wizard(self, state):
        self._get_instagram_oauth_wizard(state).unlink()

    def get_access_token_instagram(self, code, state):
        """Exchange the OAuth2 authorization code for an access token."""
        wizard_social_account = self._get_instagram_oauth_wizard(state)
        if not wizard_social_account:
            raise UserError(
                self.env._(
                    "Invalid OAuth state token. Please restart the "
                    "account association process."
                )
            )
        app_id = wizard_social_account.instagram_app_id
        app_secret = wizard_social_account.instagram_app_secret
        response = requests.post(
            _URL_TOKEN_INSTAGRAM,
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._instagram_redirect_uri(),
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Instagram token exchange failed: %(error)s", error=response.text
                )
            )
        payload = response.json()
        # The Business Login answer travels flat in the documentation and
        # under ``data`` in the exchange; both shapes carry the same token.
        access_token = payload.get("access_token") or (
            (payload.get("data") or [{}])[0].get("access_token")
        )
        if not access_token:
            raise UserError(
                self.env._(
                    "Instagram answered without an access token: %(error)s",
                    error=response.text,
                )
            )
        long_lived = requests.get(
            f"{_URL_GRAPH}access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": app_secret,
                "access_token": access_token,
            },
            timeout=30,
        )
        if long_lived.status_code != 200:
            raise UserError(
                self.env._(
                    "Instagram long-lived token exchange failed: %(error)s",
                    error=long_lived.text,
                )
            )
        data = long_lived.json()
        access_token = data.get("access_token", access_token)
        expires_in = data.get("expires_in")
        return app_id, app_secret, access_token, expires_in

    def _refresh_instagram_token(self):
        """Renew the long-lived token of this account.

        The Instagram Login API refreshes a long-lived token with the token
        itself, without the app secret, so a scheduled pass can keep the
        account alive without asking the user.
        """
        self.ensure_one()
        response = requests.get(
            f"{_URL_GRAPH}refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": self.sudo().instagram_access_token,
            },
            timeout=30,
        )
        if response.status_code in (400, 401, 403):
            raise SocialCredentialsError(
                f"Instagram refused the credentials ({response.status_code}): "
                f"{response.text}"
            )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Instagram token refresh failed: %(error)s", error=response.text
                )
            )
        data = response.json()
        values = {"instagram_access_token": data.get("access_token")}
        if data.get("expires_in"):
            values["expire_access_token_date"] = fields.Date.today() + timedelta(
                seconds=data["expires_in"]
            )
        self.sudo().write(values)
        return data.get("access_token")

    def validate_access_token(self):
        """Renew the Instagram token before its date, or flag the account.

        The refresh endpoint only accepts a token that is still valid, so the
        renewal runs ahead of the stored date. Once it has passed there is
        nothing left to do but ask the user to authorize the account again.
        """
        res = super().validate_access_token()
        if self.media_type != "instagram":
            return res
        expire = self.sudo().expire_access_token_date
        if not expire:
            return res
        if expire - fields.Date.today() > timedelta(days=_TOKEN_MARGIN_DAYS_INSTAGRAM):
            return res
        try:
            self._refresh_instagram_token()
        except (UserError, SocialCredentialsError) as error:
            raise SocialCredentialsError(
                self.env._(
                    "The Instagram credentials could not be renewed: %(error)s",
                    error=error,
                )
            ) from error
        return res

    def _refresh_credentials(self):
        if self.media_type != "instagram":
            return super()._refresh_credentials()
        try:
            return bool(self._refresh_instagram_token())
        except (UserError, SocialCredentialsError) as error:
            _logger.warning("Instagram credentials could not be renewed: %s", error)
            return False

    def _instagram_check_response(self, response, action):
        """Raise the error that matches a failed Instagram call.

        A refused credential (HTTP 401/403 or the OAuth code 190) is raised
        as ``SocialCredentialsError`` so the publication flags the account;
        anything else is an operational error of the call itself.

        :param response: the ``requests`` response to inspect.
        :param str action: what was being done, for the message.
        """
        if response.status_code == 200:
            return
        code = 0
        try:
            code = response.json().get("error", {}).get("code", 0)
        except ValueError:
            code = 0
        if response.status_code in (401, 403) or code == 190:
            raise SocialCredentialsError(
                f"Instagram refused the credentials ({response.status_code}): "
                f"{response.text}"
            )
        raise UserError(
            self.env._("%(action)s: %(error)s", action=action, error=response.text)
        )

    def _get_instagram_profile(self, access_token):
        """Return the profile of the user the access token belongs to."""
        response = requests.get(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/me",
            params={
                "fields": (
                    "id,username,account_type,profile_picture_url,followers_count"
                ),
                "access_token": access_token,
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Instagram profile lookup failed: %(error)s",
                    error=response.text,
                )
            )
        return response.json()

    def _instagram_profile_image(self, url):
        """Download the profile picture of the account, if Instagram offers one."""
        if not url:
            return False
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            return False
        return base64.b64encode(response.content)

    def create_instagram_accounts(
        self, app_id, app_secret, access_token, expires_in=None
    ):
        """Create the account of the Instagram user that authorized Odoo."""
        profile = self._get_instagram_profile(access_token)
        ig_account_id = profile.get("id") or profile.get("user_id")
        username = profile.get("username", "")
        if not ig_account_id:
            raise UserError(self.env._("Could not find any Instagram account to add."))
        existing = self._find_account_to_associate(
            "instagram", ig_account_id, username=username
        )
        if existing:
            existing._check_can_associate()
        values = {
            "remote_ref": ig_account_id,
            "name": username or ig_account_id,
            "username": username,
            "media_id": self.env.ref(
                "social_media_instagram.social_media_instagram"
            ).id,
            "instagram_account_id": ig_account_id,
            "instagram_access_token": access_token,
            "instagram_app_id": app_id,
            "instagram_app_secret": app_secret,
        }
        if expires_in:
            values["expire_access_token_date"] = fields.Date.today() + timedelta(
                seconds=expires_in
            )
        image = self._instagram_profile_image(profile.get("profile_picture_url"))
        if image:
            values["image_1920"] = image
        if existing:
            if not existing.active:
                values["active"] = True
            account = existing
            account.sudo().write(values)
        else:
            account = self.sudo().create(dict(values, user_id=self.env.user.id))
        account._trigger_initial_sync()
        with account._account_guard(
            "Error importing the publications of the account %s"
        ):
            account._instagram_import_posts()

    def _instagram_import_posts(self):
        """Import the publications of this account from the Instagram feed.

        The feed is walked newest first and the walk stops at the first
        publication already imported: the following passes only pay for what
        is new, and the first one is bounded by the number of pages read.

        :return: the imported publications.
        :rtype: recordset of ``social.post.account``
        """
        self.ensure_one()
        imported = self.env["social.post.account"]
        access_token = self.sudo().instagram_access_token
        if not access_token:
            return imported
        url = f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().instagram_account_id}/media"
        params = {
            "access_token": access_token,
            "fields": (
                "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
            ),
            "limit": _IMPORT_BATCH_SIZE,
        }
        for _page in range(_IMPORT_MAX_PAGES):
            if not url:
                break
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "Instagram publications lookup failed: %(error)s",
                        error=response.text,
                    )
                )
            payload = response.json()
            for item in payload.get("data", []):
                if self._instagram_post_is_imported(item.get("id")):
                    return imported
                imported |= self._instagram_import_post(item, access_token)
            url = payload.get("paging", {}).get("next")
            params = {}
        return imported

    def _instagram_post_is_imported(self, remote_ref):
        """Whether this account already carries the publication ``remote_ref``."""
        if not remote_ref:
            return False
        return bool(
            self.env["social.post.account"]
            .sudo()
            .with_context(active_test=False)
            .search_count(
                [("account_id", "=", self.id), ("remote_ref", "=", remote_ref)]
            )
        )

    def _instagram_import_post(self, item, access_token):
        """Create the post and the publication Odoo keeps of a feed media.

        The post is what makes the publication show up in *Posts* and not only
        on the dashboard: an imported publication carrying one is readable
        there like any other, and the figures of its account aggregate it.
        """
        remote_ref = item.get("id")
        message = item.get("caption") or ""
        published_date = self._instagram_timestamp(item.get("timestamp"))
        media = self._instagram_media_attachments(item, access_token)
        post = (
            self.env["social.post"]
            .sudo()
            .create(
                {
                    "message": message,
                    "account_ids": [(6, 0, [self.id])],
                    "image_ids": [(6, 0, media["images"].ids)],
                    "video_ids": [(6, 0, media["videos"].ids)],
                    "state": "published",
                    "published_date": published_date,
                }
            )
        )
        return (
            self.env["social.post.account"]
            .sudo()
            .create(
                {
                    "post_id": post.id,
                    "account_id": self.id,
                    "message": message,
                    "state": "posted",
                    "published_date": published_date,
                    "remote_ref": remote_ref,
                    "post_account_url": item.get("permalink"),
                    "has_video": item.get("media_type") == "VIDEO",
                    "image_ids": [(6, 0, media["images"].ids)],
                    "video_ids": [(6, 0, media["videos"].ids)],
                    "media_refs": media["refs"],
                }
            )
        )

    def _instagram_media_attachments(self, item, access_token):
        """Download the media of a feed item and return the attachments.

        An image is stored in Odoo; a video is not, its cover is. The file of
        a video is heavy and the publication already points at Instagram, which
        is where it is watched, so the cover is what the card has to show.

        :rtype: dict
        """
        images = self.env["ir.attachment"]
        refs = {}
        media_type = item.get("media_type")
        if media_type == "CAROUSEL_ALBUM":
            for child in self._instagram_children(item.get("id"), access_token):
                # A video child is published from its cover, not from its
                # file: an MP4 stored as an image is drawn as one and breaks
                # the gallery.
                if child.get("media_type") == "VIDEO":
                    image_url = child.get("thumbnail_url")
                else:
                    image_url = child.get("media_url") or child.get("thumbnail_url")
                attachment = self._instagram_download(
                    f"{item.get('id')}-{child.get('id')}", image_url
                )
                if attachment:
                    images |= attachment
                    refs[str(attachment.id)] = image_url
        elif media_type == "IMAGE":
            attachment = self._instagram_download(item.get("id"), item.get("media_url"))
            if attachment:
                images |= attachment
                refs[str(attachment.id)] = item.get("media_url")
        else:
            cover = item.get("thumbnail_url")
            attachment = self._instagram_download(f"{item.get('id')}-cover", cover)
            if attachment:
                images |= attachment
                refs[str(attachment.id)] = cover
        return {
            "images": images,
            "videos": self.env["ir.attachment"],
            "refs": refs,
        }

    def _instagram_children(self, remote_ref, access_token):
        """Return the children of a carousel publication, following pages."""
        children = []
        url = f"{_URL_GRAPH}{_GRAPH_VERSION}/{remote_ref}/children"
        params = {
            "access_token": access_token,
            "fields": "id,media_type,media_url,thumbnail_url",
            "limit": _IMPORT_BATCH_SIZE,
        }
        while url:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "Instagram carousel lookup failed: %(error)s",
                        error=response.text,
                    )
                )
            payload = response.json()
            children.extend(payload.get("data", []))
            url = payload.get("paging", {}).get("next")
            params = {}
        return children

    def _instagram_download(self, name, url):
        """Download a media and store it as an attachment, if it answers."""
        if not url:
            return self.env["ir.attachment"]
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            return self.env["ir.attachment"]
        mimetype = response.headers.get("Content-Type", "image/jpeg")
        return (
            self.env["ir.attachment"]
            .sudo()
            .create(
                {
                    "name": name,
                    "datas": base64.b64encode(response.content).decode(),
                    "mimetype": mimetype,
                }
            )
        )

    def _instagram_timestamp(self, timestamp):
        """Return the naive UTC datetime of an ISO-8601 Instagram timestamp."""
        if not timestamp:
            return False
        return (
            date_parser.isoparse(timestamp)
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    def refresh_dashboard_statistics(self):
        """Import the feed of the Instagram accounts and refresh the figures.

        What the dashboard calls when somebody presses *Update*: the feed is
        walked before the figures are read, so the counters of the imported
        publications are the ones of this very pass.
        """
        accounts = self or self.sudo().search([], limit=None)
        for account in accounts.filtered(lambda acc: acc.media_type == "instagram"):
            with account._account_guard(
                "Error importing the publications of the account %s"
            ):
                account._instagram_import_posts()
        return super().refresh_dashboard_statistics()

    def _run_check_media_updates(self):
        """Import the new publications of the Instagram accounts.

        The accounts of every other social media keep the credentials check
        of the base pass: the import is the only thing Instagram adds here.
        """
        result = super()._run_check_media_updates()
        imported = self.env["social.post.account"]
        accounts = self.sudo().search([("media_type", "=", "instagram")])
        for account in accounts:
            with account._account_guard(
                "Error importing the publications of the account %s"
            ):
                imported |= account._instagram_import_posts()
        return bool(result or imported)

    def _update_account_data(self):
        if self.media_type != "instagram":
            return super()._update_account_data()
        profile = self._get_instagram_profile(self.sudo().instagram_access_token)
        values = {}
        username = profile.get("username")
        if username:
            values["name"] = username
            values["username"] = username
        image = self._instagram_profile_image(profile.get("profile_picture_url"))
        if image:
            values["image_1920"] = image
        if profile.get("followers_count") is not None:
            values["follower_count"] = profile["followers_count"]
        if values:
            self.write(values)

    def _post_instagram_media(self, post_account):
        """Create the media container(s) and publish the Instagram post."""
        videos = post_account.post_id.video_ids
        if videos:
            return self._post_instagram_reel(post_account)
        images = post_account.post_id.image_ids
        if not images:
            raise UserError(self.env._("Instagram posts require at least one image."))
        endpoint = f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().instagram_account_id}"
        media_url = f"{endpoint}/media"
        session = requests.Session()

        container_ids = []
        for image in images:
            data = {
                "access_token": self.sudo().instagram_access_token,
                "image_url": self._media_public_url(
                    "/social_instagram/get_image", image
                ),
            }
            if len(images) == 1:
                data["caption"] = post_account.message or ""
            else:
                data["is_carousel_item"] = True
            media_response = session.post(media_url, data=data, timeout=30)
            self._instagram_check_response(
                media_response, self.env._("Instagram media container failed")
            )
            if not media_response.json().get("id"):
                raise UserError(
                    self.env._("Instagram did not return the container of the media.")
                )
            container_ids.append(media_response.json()["id"])

        if len(container_ids) > 1:
            carousel_response = session.post(
                media_url,
                json={
                    "caption": post_account.message or "",
                    "access_token": self.sudo().instagram_access_token,
                    "media_type": "CAROUSEL",
                    "children": ",".join(container_ids),
                },
                timeout=30,
            )
            self._instagram_check_response(
                carousel_response,
                self.env._("Instagram carousel container failed"),
            )
            if not carousel_response.json().get("id"):
                raise UserError(
                    self.env._("Instagram did not return the carousel container.")
                )
            container_id = carousel_response.json()["id"]
        else:
            container_id = container_ids[0]

        container_id = self._wait_instagram_container(container_id)
        return self._publish_instagram_container(container_id)

    def _post_instagram_reel(self, post_account):
        """Create and publish a reel with the video of the post."""
        video = post_account.post_id.video_ids[0]
        endpoint = f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().instagram_account_id}"
        media_response = requests.post(
            f"{endpoint}/media",
            data={
                "access_token": self.sudo().instagram_access_token,
                "media_type": "REELS",
                "video_url": self._media_public_url(
                    "/social_instagram/get_video", video
                ),
                "caption": post_account.message or "",
                "share_to_feed": "true",
            },
            timeout=30,
        )
        self._instagram_check_response(
            media_response, self.env._("Instagram reel container failed")
        )
        if not media_response.json().get("id"):
            raise UserError(
                self.env._("Instagram did not return the container of the reel.")
            )
        container_id = self._wait_instagram_container(media_response.json()["id"])
        return self._publish_instagram_container(container_id)

    def _wait_instagram_container(self, container_id):
        """Poll the container until it is processed by Instagram."""
        for _attempt in range(_STATUS_CONTAINER_POLL_ATTEMPTS):
            status_response = requests.get(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{container_id}",
                params={
                    "access_token": self.sudo().instagram_access_token,
                    "fields": "status_code",
                },
                timeout=30,
            )
            if status_response.status_code != 200:
                self._instagram_check_response(
                    status_response,
                    self.env._("Instagram container status failed"),
                )
            status_code = status_response.json().get("status_code")
            if status_code == "FINISHED":
                return container_id
            if status_code in _STATUS_CONTAINER_ERROR:
                raise UserError(
                    self.env._(
                        "Instagram media container failed to process "
                        "(status %(status)s).",
                        status=status_code,
                    )
                )
            time.sleep(_STATUS_CONTAINER_POLL_DELAY)
        raise UserError(
            self.env._("Instagram media container timed out while processing.")
        )

    def _publish_instagram_container(self, container_id):
        publish_response = requests.post(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().instagram_account_id}/media_publish",
            data={
                "access_token": self.sudo().instagram_access_token,
                "creation_id": container_id,
            },
            timeout=30,
        )
        self._instagram_check_response(
            publish_response, self.env._("Instagram publish failed")
        )
        return publish_response.json().get("id")

    def _delete_instagram_media(self, post_account):
        if not post_account.remote_ref:
            return {"success": True, "message": ""}
        raise UserError(
            self.env._(
                "The Instagram API with Instagram Login does not allow deleting "
                "publications: delete it in the Instagram app and archive the "
                "publication here to keep its history."
            )
        )

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures Instagram reports for these publications.

        :param post_accounts: the lines to read, every one with a ``remote_ref``.
        :rtype: recordset
        """
        instagram = post_accounts.filtered(
            lambda line: line.account_id.media_type == "instagram"
        )
        refreshed = super()._refresh_post_statistics(post_accounts - instagram)
        if not instagram:
            return refreshed
        return refreshed | self._instagram_write_post_statistics(instagram)

    def _instagram_write_post_statistics(self, post_accounts):
        """Ask Instagram for these publications and write what it answers."""
        self.ensure_one()
        access_token = self.sudo().instagram_access_token
        read_on = fields.Datetime.now()
        for line in post_accounts:
            response = requests.get(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{line.remote_ref}",
                params={
                    "access_token": access_token,
                    "fields": "like_count,comments_count",
                },
                timeout=30,
            )
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "Instagram statistics failed: %(error)s",
                        error=response.text,
                    )
                )
            data = response.json()
            line.sudo().write(
                {
                    "like_count": data.get("like_count", 0),
                    "comment_count": data.get("comments_count", 0),
                    "statistics_date": read_on,
                }
            )
        return post_accounts
