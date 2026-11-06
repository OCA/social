# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
from urllib.parse import urljoin

import requests

from odoo import fields, models
from odoo.exceptions import UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_facebook_utils import _GRAPH_VERSION, _URL_GRAPH

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """Facebook implementation of the social account API calls."""

    _inherit = "social.account"

    facebook_account_id = fields.Char(groups="base.group_system")
    facebook_access_token = fields.Char(groups="base.group_system")
    facebook_app_id = fields.Char(string="Facebook App ID", groups="base.group_system")
    facebook_app_secret = fields.Char(groups="base.group_system")

    def _facebook_redirect_uri(self):
        return urljoin(self.get_base_url(), "/social_facebook/callback")

    def _facebook_check_error(self, response, action):
        """Raise the error that matches a failed Facebook call.

        Only the OAuth error codes mean the credentials (190) or the session
        (102, 463) are dead: a 403 with any other code is a permission the
        app or the user is missing, and asking again for the token does not
        fix it.

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
        if code in (102, 190, 463):
            raise SocialCredentialsError(
                f"Facebook refused the credentials ({response.status_code}): "
                f"{response.text}"
            )
        raise UserError(
            self.env._("%(action)s: %(error)s", action=action, error=response.text)
        )

    def _fields_account_url(self):
        urls = super()._fields_account_url()
        if self.media_type == "facebook" and self.sudo().facebook_account_id:
            urls["facebook"] = (
                f"https://www.facebook.com/{self.sudo().facebook_account_id}"
            )
        return urls

    def _get_removal_values(self):
        res = super()._get_removal_values()
        res.update(
            {
                "facebook_access_token": False,
                "facebook_account_id": False,
                "facebook_app_id": False,
                "facebook_app_secret": False,
            }
        )
        return res

    def _get_facebook_oauth_wizard(self, state):
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

    def _consume_facebook_oauth_wizard(self, state):
        self._get_facebook_oauth_wizard(state).unlink()

    def get_access_token_facebook(self, code, state):
        """Exchange the OAuth2 authorization code for an access token."""
        wizard_social_account = self._get_facebook_oauth_wizard(state)
        if not wizard_social_account:
            raise UserError(
                self.env._(
                    "Invalid OAuth state token. Please restart the "
                    "account association process."
                )
            )
        app_id = wizard_social_account.facebook_app_id
        app_secret = wizard_social_account.facebook_app_secret
        response = requests.post(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/oauth/access_token",
            data={
                "client_id": app_id,
                "client_secret": app_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self._facebook_redirect_uri(),
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Facebook token exchange failed: %(error)s", error=response.text
                )
            )
        access_token = response.json().get("access_token")
        long_lived = requests.get(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": access_token,
            },
            timeout=30,
        )
        if long_lived.status_code != 200:
            raise UserError(
                self.env._(
                    "Facebook long-lived token exchange failed: %(error)s",
                    error=long_lived.text,
                )
            )
        access_token = long_lived.json().get("access_token", access_token)
        return app_id, app_secret, access_token

    def _get_facebook_pages(self, access_token):
        """Return every Facebook page of the user, following pagination."""
        pages = []
        url = f"{_URL_GRAPH}{_GRAPH_VERSION}/me/accounts"
        params = {
            "fields": "access_token,name,id",
            "access_token": access_token,
            "limit": 100,
        }
        while url:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "Facebook page lookup failed: %(error)s",
                        error=response.text,
                    )
                )
            data = response.json()
            pages.extend(data.get("data", []))
            url = data.get("paging", {}).get("next")
            params = {}
        return pages

    def create_facebook_accounts(self, app_id, app_secret, access_token):
        """Create one account per Facebook page the user manages."""
        pages = self._get_facebook_pages(access_token)
        if not pages:
            raise UserError(self.env._("Could not find any Facebook page to add."))
        created = False
        for page in pages:
            page_id = page.get("id")
            page_access_token = page.get("access_token")
            if not page_id or not page_access_token:
                continue
            existing = self._find_account_to_associate(
                "facebook", page_id, username=page.get("name")
            )
            if existing:
                existing._check_can_associate()
            values = {
                "remote_ref": page_id,
                "name": page.get("name"),
                "username": page.get("name"),
                "media_id": self.env.ref(
                    "social_media_facebook.social_media_facebook"
                ).id,
                "facebook_account_id": page_id,
                "facebook_access_token": page_access_token,
                "facebook_app_id": app_id,
                "facebook_app_secret": app_secret,
            }
            if existing:
                if not existing.active:
                    values["active"] = True
                existing.sudo().write(values)
            else:
                self.sudo().create(dict(values, user_id=self.env.user.id))
            created = True
        if not created:
            raise UserError(
                self.env._("You need to manage at least one Facebook page.")
            )
        self._trigger_initial_sync()

    def _update_account_data(self):
        if self.media_type != "facebook":
            return super()._update_account_data()
        response = requests.get(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}",
            params={
                "fields": "name,username,fan_count,followers_count",
                "access_token": self.sudo().facebook_access_token,
            },
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            self.write(
                {
                    "name": data.get("name"),
                    "username": data.get("username") or data.get("name"),
                    "follower_count": data.get("followers_count")
                    or data.get("fan_count")
                    or 0,
                }
            )
        else:
            _logger.warning(
                "Facebook account data refresh failed for account %s: %s",
                self.id,
                response.text,
            )

    def validate_access_token(self):
        """Check the page token against Facebook when the user asks for it.

        The stored page token carries no readable expiry on our side, so its
        dates cannot tell a revoked token from a working one: only a call
        does. It is made when the user asks from the account form, not before
        every operation.
        """
        res = super().validate_access_token()
        if self.media_type == "facebook" and self.env.context.get("check_remote_token"):
            response = requests.get(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}",
                params={
                    "fields": "id",
                    "access_token": self.sudo().facebook_access_token,
                },
                timeout=30,
            )
            self._facebook_check_error(
                response, self.env._("Facebook token check failed")
            )
        return res

    def _refresh_credentials(self):
        if self.media_type != "facebook":
            return super()._refresh_credentials()
        # A page token is re-issued only from the user token, which is not
        # stored: Facebook credentials cannot be renewed without the user.
        return False

    def _post_facebook(self, post_account):
        """Publish a text, single image or multi image post on the page."""
        if post_account.post_id.video_ids:
            return self._post_facebook_video(post_account)
        images = post_account.post_id.image_ids
        if len(images) > 1:
            return self._post_facebook_album(post_account)
        message = post_account.message or ""
        if len(images) == 1:
            image = images[0]
            response = requests.post(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}/photos",
                data={
                    "access_token": self.sudo().facebook_access_token,
                    "caption": message,
                    "url": self._media_public_url("/social_facebook/get_image", image),
                },
                timeout=30,
            )
        else:
            response = requests.post(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}/feed",
                data={
                    "access_token": self.sudo().facebook_access_token,
                    "message": message,
                },
                timeout=30,
            )
        self._facebook_check_error(response, self.env._("Facebook publish failed"))
        result = response.json()
        return result.get("post_id", result.get("id"))

    def _post_facebook_album(self, post_account):
        """Publish a multi image post as a Facebook album."""
        photo_ids = []
        for image in post_account.post_id.image_ids:
            response = requests.post(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}/photos",
                data={
                    "access_token": self.sudo().facebook_access_token,
                    "url": self._media_public_url("/social_facebook/get_image", image),
                    "published": "false",
                },
                timeout=30,
            )
            self._facebook_check_error(
                response, self.env._("Facebook album upload failed")
            )
            photo_id = response.json().get("id")
            if photo_id:
                photo_ids.append(photo_id)
        response = requests.post(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}/feed",
            data={
                "access_token": self.sudo().facebook_access_token,
                "message": post_account.message or "",
                "attached_media": json.dumps(
                    [{"media_fbid": photo_id} for photo_id in photo_ids]
                ),
            },
            timeout=30,
        )
        self._facebook_check_error(response, self.env._("Facebook publish failed"))
        result = response.json()
        return result.get("post_id", result.get("id"))

    def _post_facebook_video(self, post_account):
        """Publish a video on the Facebook page."""
        video = post_account.post_id.video_ids[0]
        response = requests.post(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/{self.sudo().facebook_account_id}/videos",
            data={
                "access_token": self.sudo().facebook_access_token,
                "description": post_account.message or "",
                "file_url": self._media_public_url("/social_facebook/get_video", video),
            },
            timeout=60,
        )
        self._facebook_check_error(response, self.env._("Facebook publish failed"))
        result = response.json()
        return result.get("post_id", result.get("id"))

    def _delete_facebook_post(self, post_account):
        if not post_account.remote_ref:
            return {"success": True, "message": ""}
        response = requests.delete(
            f"{_URL_GRAPH}{_GRAPH_VERSION}/{post_account.remote_ref}",
            params={"access_token": self.sudo().facebook_access_token},
            timeout=30,
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Facebook post deletion failed: %(error)s", error=response.text
                )
            )
        return {"success": True, "message": ""}

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures Facebook reports for these publications.

        The Graph API answers a whole page of posts in a single call when
        their ids travel together, so the counters of the batch come back at
        once and only the lines of this social media are written.

        :param post_accounts: the lines to read, every one with a ``remote_ref``.
        :rtype: recordset
        """
        facebook = post_accounts.filtered(
            lambda line: line.account_id.media_type == "facebook"
        )
        refreshed = super()._refresh_post_statistics(post_accounts - facebook)
        if not facebook:
            return refreshed
        return refreshed | self._facebook_write_post_statistics(facebook)

    def _facebook_write_post_statistics(self, post_accounts):
        """Ask Facebook for these publications and write what it answers.

        The root ``GET /?ids=...`` request was removed in Graph API v26, so
        the figures are read one publication at a time.
        """
        self.ensure_one()
        read_on = fields.Datetime.now()
        for line in post_accounts:
            response = requests.get(
                f"{_URL_GRAPH}{_GRAPH_VERSION}/{line.remote_ref}",
                params={
                    "access_token": self.sudo().facebook_access_token,
                    "fields": "likes.summary(true).limit(0),"
                    "comments.summary(true).limit(0),shares",
                },
                timeout=30,
            )
            if response.status_code != 200:
                raise UserError(
                    self.env._(
                        "Facebook statistics failed: %(error)s", error=response.text
                    )
                )
            data = response.json()
            line.sudo().write(
                {
                    "like_count": data.get("likes", {})
                    .get("summary", {})
                    .get("total_count", 0),
                    "comment_count": data.get("comments", {})
                    .get("summary", {})
                    .get("total_count", 0),
                    "share_count": data.get("shares", {}).get("count", 0),
                    "statistics_date": read_on,
                }
            )
        return post_accounts
