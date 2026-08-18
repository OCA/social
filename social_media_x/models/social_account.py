# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import itertools
import logging
import time
from datetime import datetime

import pytz
import requests
import tweepy
from markupsafe import Markup, escape
from tweepy.errors import TooManyRequests

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..social_x_utils import (
    _URL_OAUTH2_TOKEN_X,
    _URL_OAUTH_X,
    _URL_PRICING_X,
    _URL_RATE_LIMITS_X,
    _URL_X,
    _get_oauth,
    _is_app_without_paid_plan,
)

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """X implementation of the social account API calls."""

    _inherit = "social.account"

    x_access_token_oauth2 = fields.Char(
        string="Token for read", help="Read tweets", groups="base.group_system"
    )
    x_access_token_oauth1 = fields.Char(
        string="Token for write",
        help="Post, like, comment, answer",
        groups="base.group_system",
    )
    x_access_secret_oauth1 = fields.Char(groups="base.group_system")
    x_api_key = fields.Char(string="API Key", groups="base.group_system")
    x_api_secret = fields.Char(string="API Secret", groups="base.group_system")
    retweet_count = fields.Integer(default=0)
    quote_count = fields.Integer(default=0)
    rate_limit_endpoint = fields.Json(copy=False, default=dict)
    last_post_id = fields.Char()
    enable_since = fields.Boolean(
        default=False,
        help="Read only the posts published after the last one already "
        "synchronized, to consume fewer API requests. The metrics of the "
        "previous posts are no longer updated while this option is on.",
    )
    post_since_id = fields.Many2one(
        "social.post.account",
        compute="_compute_post_since_id",
        store=True,
        domain=[("media_type", "=", "x")],
        help="This post is updated with each request with the latest one.",
    )
    engagement = fields.Float(
        default=0,
        compute="_compute_engagement",
        inverse="_inverse_engagement",
        store=True,
    )

    @api.depends("interactions_count", "impression_count")
    def _compute_engagement(self):
        for account in self:
            if account.media_type == "x":
                account.engagement = (
                    (account.interactions_count / account.impression_count) * 100
                    if account.impression_count > 0
                    else 0
                )
            else:
                account.engagement = account.engagement or 0

    def _inverse_engagement(self):
        """Allow direct writes from other social media modules."""

    @api.depends(
        "retweet_count",
        "quote_count",
        "click_count",
        "like_count",
        "share_count",
        "comment_count",
    )
    def _compute_interactions_count(self):
        res = super()._compute_interactions_count()
        for account in self:
            account.interactions_count = (
                account.click_count
                + account.like_count
                + account.share_count
                + account.comment_count
                + account.retweet_count
                + account.quote_count
            )
        return res

    @api.onchange("enable_since")
    def _onchange_post_since_id(self):
        for account in self:
            if not account.enable_since:
                account.post_since_id = False
                account.last_post_id = False

    @api.depends(
        "last_post_id",
        "enable_since",
        "post_account_ids.remote_ref",
        "post_account_ids.published_date",
    )
    def _compute_post_since_id(self):
        SocialPostAccount = self.env["social.post.account"]
        for account in self:
            if not account.enable_since:
                account.post_since_id = False
                continue
            domain = [("account_id", "=", account.id)]
            if account.last_post_id:
                domain.append(("remote_ref", "=", account.last_post_id))
            account.post_since_id = SocialPostAccount.search(
                domain, limit=1, order="published_date desc"
            ).id

    def _get_group_account_username(self):
        """Group these accounts by username to detect duplicated X users.

        :return: Tuples of username and number of accounts using it.
        :rtype: list
        """
        return self._read_group(
            domain=[("id", "in", self.ids)],
            groupby=["username"],
            aggregates=["__count"],
        )

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "x",
                f"{_URL_X}{self.username}",
            )
        ]

    def _valid_time_request(self, endpoint="get_tweets"):
        """Return whether the rate limit window of the endpoint is already over.

        :rtype: bool
        """
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        now = datetime.now(timezone).replace(tzinfo=None)
        limit_reset = (
            self.rate_limit_endpoint.get(endpoint, {}).get("x-rate-limit-reset", False)
            if self.rate_limit_endpoint
            else None
        )
        if (
            limit_reset
            and datetime.fromtimestamp(limit_reset, tz=timezone).replace(tzinfo=None)
            >= now
        ):
            return self._get_message_many_requests(endpoint=endpoint)
        return True

    def _get_message_many_requests(
        self, ex=None, endpoint="get_tweets", view_type="kanban"
    ):
        """Store the rate limit headers and tell the user when to retry.

        :param ex: the TooManyRequests error carrying the headers, if any.
        :return: True when no limit is known, False once the user is warned.
        :rtype: bool
        """
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        if ex:
            headers = ex.response.headers
            rate_limit_endpoint = dict(self.rate_limit_endpoint or {})
            rate_limit_endpoint[endpoint] = {
                "x-rate-limit-limit": int(headers.get("x-rate-limit-limit", 0)),
                "x-rate-limit-remaining": int(headers.get("x-rate-limit-remaining", 0)),
                "x-rate-limit-reset": int(
                    headers.get("x-rate-limit-reset", time.time() + 60)
                ),
            }
            self.write({"rate_limit_endpoint": rate_limit_endpoint})
        if not self.rate_limit_endpoint:
            return True
        limit_reset = self.rate_limit_endpoint.get(endpoint, {}).get(
            "x-rate-limit-reset", 0
        )
        next_valid_request = limit_reset and datetime.fromtimestamp(
            limit_reset, tz=timezone
        ).replace(tzinfo=None)
        # Built as markup so that the notifications keep the tags. The rate
        # limit values come from the headers of X, so they are escaped. They
        # are escaped into plain strings on purpose: a ``Markup`` argument
        # makes the translation escape the whole message.
        message = Markup(
            self.env._(
                "You have reached the limit of requests <b>%(endpoint)s</b> "
                "allowed according to your account plan."
                "<br>\u2022\u2009<b>Total limit:</b> %(limit)s request(s) per "
                "window or period"
                "<br>\u2022\u2009<b>Remaining:</b> %(remaining)s"
                "<br>\u2022\u2009<b>Next request:</b> %(next_request)s<br>"
                "Please try again after that time (Next request).<br>"
                "For more information, see the "
                "<a href='%(rate_limit_url)s' target='_blank'>rate limits</a>.",
                limit=str(
                    escape(
                        self.rate_limit_endpoint.get(endpoint, {}).get(
                            "x-rate-limit-limit", 0
                        )
                    )
                ),
                remaining=str(
                    escape(
                        self.rate_limit_endpoint.get(endpoint, {}).get(
                            "x-rate-limit-remaining", 0
                        )
                    )
                ),
                next_request=next_valid_request,
                endpoint=endpoint.replace("_", " ").capitalize(),
                rate_limit_url=_URL_RATE_LIMITS_X,
            )
        )
        _logger.info(message)
        self._notify_user_client(
            notif_type=f"social_{view_type}_info",
            notif_message=message,
            media="X",
            account_name=self.name,
        )
        return False

    def _get_access_token_oauth2(self, wizard_social_account=None):
        """Return the app-only bearer token used for the read endpoints."""
        account_sudo = self.sudo()
        credentials = (
            f"{wizard_social_account.x_api_key or account_sudo.x_api_key}:"
            f"{wizard_social_account.x_api_secret or account_sudo.x_api_secret}"
        ).encode()
        b64_credentials = base64.b64encode(credentials).decode("utf-8")
        url = _URL_OAUTH2_TOKEN_X
        headers = {
            "Authorization": f"Basic {b64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, data=data, timeout=10)
        token = response.json().get("access_token", False)
        return token

    @api.model
    def _x_error_message(self, error, pricing_link=None):
        """Explain the error of X, telling apart the missing paid plan.

        The message is rendered as HTML by the notifications, so the answer of
        X is escaped: it is third party content and it must never be trusted
        as markup.

        :param pricing_link: what to write in place of the link to the pricing
            page. An anchor by default, so that the message can be rendered as
            it is; the sinks that escape the message pass their own
            placeholder instead.
        :return: The message to show to the user.
        :rtype: markupsafe.Markup
        """
        if _is_app_without_paid_plan(error):
            if pricing_link is None:
                # Plain string on purpose: a ``Markup`` argument makes the
                # translation escape the whole message.
                pricing_link = str(
                    Markup("<a href='%s' target='_blank'>%s</a>")
                    % (_URL_PRICING_X, self.env._("X API pricing"))
                )
            return Markup(
                self.env._(
                    "X rejected the request because the developer App is not "
                    "enrolled in a paid plan. The X API no longer has a free "
                    "access tier: attach the App to a Project and subscribe a "
                    "plan at %(pricing_link)s, then try again.",
                    pricing_link=pricing_link,
                )
            )
        return escape(str(error))

    @api.model
    def _get_x_oauth_wizard(self, kwargs):
        """Return the association wizard that started this OAuth flow.

        OAuth 1.0a has no ``state`` parameter, so the request token is what
        ties the callback to the flow that started it. The wizard is looked
        up by that token and by its creator, so a callback cannot pick the
        wizard of another user and use their API credentials.
        """
        oauth_token = (kwargs or {}).get("oauth_token", False)
        if not oauth_token:
            raise UserError(
                self.env._(
                    "Invalid X callback: the request token is missing. "
                    "Please restart the account association process."
                )
            )
        wizard_social_account = (
            self.env["wizard.social.account"]
            .sudo()
            .search(
                [
                    ("oauth_token", "=", oauth_token),
                    ("create_uid", "=", self.env.user.id),
                ],
                limit=1,
            )
        )
        if not wizard_social_account:
            raise UserError(
                self.env._(
                    "Invalid X request token. Please restart the account "
                    "association process."
                )
            )
        return wizard_social_account

    def _get_access_token(self, kwargs):
        url = f"{_URL_OAUTH_X}/access_token"
        wizard_social_account = self._get_x_oauth_wizard(kwargs)
        account_sudo = self.sudo()
        auth = _get_oauth(
            wizard_social_account.x_api_key or account_sudo.x_api_key,
            wizard_social_account.x_api_secret or account_sudo.x_api_secret,
            request_access_token=kwargs,
        )
        oauth_verifier = kwargs.get("oauth_verifier")
        response = requests.post(
            url, auth=auth, data={"oauth_verifier": oauth_verifier}, timeout=10
        )
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Error getting X access token: %(error)s", error=response.text
                )
            )
        try:
            access_tokens = dict(x.split("=") for x in response.text.split("&"))
            return access_tokens["oauth_token"], access_tokens["oauth_token_secret"]
        except (ValueError, KeyError) as ex:
            raise UserError(
                self.env._("Unexpected response from X: %(error)s", error=response.text)
            ) from ex

    def get_client_api(
        self,
        client_api=True,
        x_access_token_oauth1=None,
        x_access_secret_oauth1=None,
        bearer_token=None,
        kwargs=None,
    ):
        """Build the tweepy client for this account.

        ``client_api`` returns the API v2 client used for reading and
        posting; otherwise the v1.1 client, still needed to upload media.

        :rtype: tweepy.Client | tweepy.API
        """
        if client_api:
            wizard_social_account = self.env["wizard.social.account"]
            if kwargs:
                wizard_social_account = self._get_x_oauth_wizard(kwargs)
            account_sudo = self.sudo()
            return tweepy.Client(
                bearer_token=account_sudo.x_access_token_oauth2 or bearer_token,
                consumer_key=account_sudo.x_api_key or wizard_social_account.x_api_key,
                consumer_secret=account_sudo.x_api_secret
                or wizard_social_account.x_api_secret,
                access_token=x_access_token_oauth1
                or account_sudo.x_access_token_oauth1,
                access_token_secret=x_access_secret_oauth1
                or account_sudo.x_access_secret_oauth1,
            )
        account_sudo = self.sudo()
        auth = tweepy.OAuth1UserHandler(
            consumer_key=account_sudo.x_api_key,
            consumer_secret=account_sudo.x_api_secret,
            access_token=x_access_token_oauth1 or account_sudo.x_access_token_oauth1,
            access_token_secret=x_access_secret_oauth1
            or account_sudo.x_access_secret_oauth1,
        )
        return tweepy.API(auth)

    def _update_account_data(self):
        client = self.get_client_api(bearer_token=self.sudo().x_access_token_oauth2)
        data = client.get_me(
            user_fields=["username", "name", "profile_image_url", "created_at"]
        ).data
        values = {
            "name": data.name,
            "username": data.username,
        }
        media_content = requests.get(data.profile_image_url, timeout=10)
        if media_content.status_code == 200:
            values.update(
                {
                    "image_1920": base64.b64encode(media_content.content),
                }
            )
        self.write(values)

    def create_account_x(self, x_access_token_oauth1, x_access_secret_oauth1, kwargs):
        """Create or update the account of the authorized X user.

        An existing account is only reused when the current user is allowed
        to associate it, and it is reactivated if it was archived.
        """
        client = self.get_client_api(
            x_access_token_oauth1=x_access_token_oauth1,
            x_access_secret_oauth1=x_access_secret_oauth1,
            kwargs=kwargs,
        )
        try:
            data = client.get_me(
                user_fields=[
                    "username",
                    "name",
                    "public_metrics",
                    "profile_image_url",
                    "created_at",
                ]
            ).data
            if data.username:
                wizard_social_account = self._get_x_oauth_wizard(kwargs)
                media_content = requests.get(data.profile_image_url, timeout=10)
                account_image = None
                if media_content.status_code == 200:
                    account_image = base64.b64encode(media_content.content)
                values = {
                    "remote_ref": data.id,
                    "name": data.name,
                    "x_api_key": wizard_social_account.x_api_key,
                    "x_api_secret": wizard_social_account.x_api_secret,
                    "username": data.username,
                    "image_1920": account_image,
                    "media_id": self.env.ref("social_media_x.social_media_x").id,
                    "x_access_token_oauth1": x_access_token_oauth1,
                    "x_access_secret_oauth1": x_access_secret_oauth1,
                }
                access_token_oauth2 = self._get_access_token_oauth2(
                    wizard_social_account
                )
                if access_token_oauth2:
                    values.update({"x_access_token_oauth2": access_token_oauth2})
                    acc_count = self._find_account_to_associate(
                        "x", str(data.id), username=data.username
                    )
                    if acc_count:
                        acc_count._check_can_associate()
                    if not acc_count:
                        self.sudo().create(dict(values, user_id=self.env.user.id))
                    else:
                        if not acc_count.active:
                            values["active"] = True
                        acc_count.sudo().write(values)
                    self._trigger_initial_sync()
                else:
                    message_error = self.env._(
                        "The account was not created: the OAuth2 access "
                        "token could not be obtained."
                    )
                    self._notify_failed_association(message_error)
                    _logger.error(message_error)
        except (AccessError, UserError):
            raise
        except TooManyRequests as exManyRequest:
            self._get_message_many_requests(exManyRequest, endpoint="create_account")
        except Exception as e:
            _logger.exception("Error reading the authorized X user")
            self._notify_failed_association(self._x_error_message(e))

    def _notify_failed_association(self, message_error):
        """Tell the user why the account of X could not be associated.

        This runs while answering the OAuth callback, which ends in a redirect
        that reloads the web client. A bus notification races with that
        reload, so the message is kept in the session instead: it is the only
        way of delivering it exactly once.
        """
        self._notify_user_session(
            self._format_user_notification(message_error, media="X")
        )

    def _prepare_medias_for_tweet(
        self, image_ids=None, video_ids=None, image_datas=None
    ):
        media_ids = []
        if image_datas:
            image_ids = [image_datas.split(",")[-1]]
        api = self.get_client_api(client_api=False)
        for media_post in list(itertools.chain(image_ids or [], video_ids or [])):
            image_file = io.BytesIO(
                base64.b64decode(media_post.datas)
                if not isinstance(media_post, str)
                else base64.b64decode(media_post)
            )
            media = api.media_upload(
                filename=(media_post.name if not isinstance(media_post, str) else False)
                or False,
                file=image_file,
            )
            media_ids.append(media.media_id)
        return media_ids

    def create_tweet(self, message, image_ids, video_ids, post_id, post_account_id):
        """Publish a post with its media.

        :return: The id of the published tweet or False.
        :rtype: str | bool
        """
        context = dict(self.env.context)
        client_api = self.get_client_api()
        try:
            medias = self._prepare_medias_for_tweet(
                image_ids=image_ids, video_ids=video_ids
            )
            if (medias and (image_ids or video_ids)) or (
                not image_ids or not video_ids
            ):
                tweet = client_api.create_tweet(
                    text=message, media_ids=medias if len(medias) > 0 else None
                )
                return tweet.data.get("id", False)
            return False
        except TooManyRequests as exManyRequest:
            if not context.get("social_post_cron", False):
                return self._get_message_many_requests(
                    exManyRequest, endpoint="create_tweet", view_type="form"
                )
            else:
                post_id._message_error_post(
                    str(exManyRequest), post_account_id.media_type
                )
                return False
        except Exception as ex:
            _logger.exception("Error publishing the post on X")
            if not context.get("social_post_cron", False):
                self._notify_user_client(
                    notif_type="social_form_danger",
                    notif_message=str(ex),
                    account_name=self.name,
                    media=self.media_type,
                )
            else:
                post_id._message_error_post(str(ex), post_account_id.media_type)
            return False

    def _get_x_statistics(self, statistics):
        return list(
            itertools.chain(
                statistics,
                self.search_read(
                    [("media_type", "=", "x")],
                    [
                        "name",
                        "company_id",
                        "media_id",
                        "impression_count",
                        "interactions_count",
                        "engagement",
                        "need_update",
                    ],
                ),
            )
        )

    def _get_users_tweets(self, since_id=None):
        """Read the timeline of this account, from ``since_id`` when given."""
        client_api = self.get_client_api(bearer_token=self.sudo().x_access_token_oauth2)
        return client_api.get_users_tweets(
            id=self.remote_ref,
            max_results=100,
            tweet_fields=[
                "id",
                "text",
                "created_at",
                "author_id",
                "public_metrics",
                "attachments",
                "entities",
                "conversation_id",
                "in_reply_to_user_id",
                "referenced_tweets",
            ],
            expansions="attachments.media_keys,author_id",
            user_fields=["profile_image_url"],
            media_fields=[
                "media_key",
                "type",
                "url",
                "variants",
                "public_metrics",
            ],
            exclude=["retweets", "replies"],
            since_id=since_id,
        )

    def _get_public_metrics(self, val_x):
        """Return the like, impression, reply, retweet and quote counts.

        :rtype: tuple
        """
        public_metrics = val_x.public_metrics
        return (
            public_metrics.get("like_count", 0),
            public_metrics.get("impression_count", 0),
            public_metrics.get("reply_count", 0),
            public_metrics.get("retweet_count", 0),
            public_metrics.get("quote_count", 0),
        )

    def _get_post_accounts_by_tweet(self, tweet_ids):
        """Prefetch post accounts by tweet id to avoid per-tweet searches."""
        post_accounts_by_tweet = {}
        if tweet_ids:
            for existing in self.env["social.post.account"].search(
                [("remote_ref", "in", tweet_ids)]
            ):
                post_accounts_by_tweet.setdefault(existing.remote_ref, existing)
        return post_accounts_by_tweet

    def _update_posts_statistics(self, post_id, domain):
        statistics = super()._update_posts_statistics(post_id, domain)
        PostAccount = self.env["social.post.account"]
        if not self:
            account_ids = self.search(
                [
                    ("media_type", "=", "x"),
                ]
            )
        elif any(val.media_type == "x" for val in self):
            account_ids = self
        else:
            return self._get_x_statistics(statistics)

        timezone = pytz.timezone(self.env.user.tz or "UTC")
        for account in account_ids:
            try:
                result = account.with_context(notify_client=True)._valid_time_request()
                if result:
                    post_accounts = []
                    since_id = (
                        account.post_since_id.remote_ref
                        if account.post_since_id
                        and account.post_since_id.remote_ref
                        and account.enable_since
                        else None
                    )
                    response = account._get_users_tweets(since_id)
                    if not response.data:
                        message_error = "<br>".join(
                            [
                                f"<br>{error.get('detail', '')}"
                                for error in response.errors
                            ]
                        )
                        _logger.error("Get Tweets: %s", message_error)
                        self._notify_user_client(
                            notif_type="social_kanban_danger",
                            notif_message=message_error,
                            media="X",
                            account_name=account.name,
                        )
                        continue
                    media_map = {
                        m.media_key: (m.media_key, m.url, m.type)
                        for m in (response.includes.get("media") or [])
                    }
                    post_accounts_by_tweet = account._get_post_accounts_by_tweet(
                        [str(val_x.id) for val_x in (response.data or []) if val_x.id]
                    )
                    like_count = 0
                    impression_count = 0
                    comment_count = 0
                    retweet_count = 0
                    quote_count = 0
                    users = {
                        str(u.id): u for u in (response.includes.get("users", []) or [])
                    }
                    for val_x in response.data or []:
                        has_quote = any(
                            rt.type == "quoted"
                            for rt in (val_x.referenced_tweets or [])
                        )
                        is_root = (val_x.conversation_id == val_x.id) and (
                            val_x.in_reply_to_user_id is None
                        )
                        if is_root and not has_quote:
                            author = users.get(str(val_x.author_id))
                            post_account = post_accounts_by_tweet.get(
                                str(val_x.id), PostAccount
                            )
                            media_keys = (getattr(val_x, "attachments", {}) or {}).get(
                                "media_keys", []
                            )
                            image_ids = None
                            if media_keys:
                                image_ids = post_account._get_assets_save_x(
                                    media_keys, media_map
                                )
                            message_text = val_x.text
                            if val_x.entities:
                                for url in getattr(val_x, "entities", {}).get(
                                    "urls", []
                                ):
                                    message_text = message_text.replace(
                                        url.get("url", ""), ""
                                    )
                            public_metrics = account._get_public_metrics(val_x)
                            like_count += public_metrics[0]
                            impression_count += public_metrics[1]
                            comment_count += public_metrics[2]
                            retweet_count += public_metrics[3]
                            quote_count += public_metrics[4]

                            data = {
                                "remote_ref": val_x.get("id"),
                                "post_account_url": (
                                    f"{_URL_X}{account.username}/status/{val_x.id}"
                                ),
                                "message": message_text,
                                "account_id": account.id,
                                "published_date": val_x.created_at.astimezone(
                                    timezone
                                ).replace(tzinfo=None),
                                "like_count": public_metrics[0],
                                "impression_count": public_metrics[1],
                                "comment_count": public_metrics[2],
                                "retweet_count": public_metrics[3],
                                "quote_count": public_metrics[4],
                                "actor_urn": val_x.author_id,
                                "state": "posted",
                                "author": author.username,
                            }
                            if image_ids:
                                data.update({"image_ids": image_ids})
                            if not post_account:
                                post_accounts.append(Command.create(data))
                            else:
                                post_accounts.append(
                                    Command.update(post_account.id, data)
                                )
                    update_account_data = {}
                    if len(post_accounts) > 0:
                        update_account_data.update({"post_account_ids": post_accounts})
                    update_account_data.update(
                        {
                            "like_count": like_count,
                            "impression_count": impression_count,
                            "retweet_count": retweet_count,
                            "quote_count": quote_count,
                            "comment_count": comment_count,
                            "last_post_id": response.meta.get("newest_id", False)
                            if account.enable_since
                            else False,
                        }
                    )
                    account.write(update_account_data)

            except TooManyRequests as exManyRequest:
                account.with_context(notify_client=True)._get_message_many_requests(
                    ex=exManyRequest
                )
            except Exception as e:
                _logger.exception("Error reading the posts of the X account")
                self._notify_user_client(
                    notif_type="social_kanban_danger",
                    notif_message=str(e),
                    media="X",
                    account_name=account.name,
                )
        return self._get_x_statistics(statistics)

    def update_account(self):
        res = super().update_account()
        if self.media_type == "x":
            account_sudo = self.sudo()
            ctx = dict(res.get("context", {}))
            ctx.update(
                {
                    "default_x_api_key": account_sudo.x_api_key,
                    "default_x_api_secret": account_sudo.x_api_secret,
                }
            )
            res["context"] = ctx
        return res

    def _get_chart_account_statistics(self, start_date, end_date, granularity):
        data = super()._get_chart_account_statistics(start_date, end_date, granularity)
        data_x = []
        if not self:
            account_ids = self.search([("media_type", "=", "x")])
        elif any(account.media_type == "x" for account in self):
            account_ids = self
        else:
            return data
        for account in account_ids:
            like_count = 0
            impression_count = 0
            comment_count = 0
            retweet_count = 0
            quote_count = 0
            try:
                update_account_data = {}
                start_date, end_date = account._get_default_filter_date(
                    start_date, end_date
                )
                if not account._valid_time_request():
                    data_x += account._map_chart_statistics(
                        [
                            (
                                0,
                                account.like_count,
                                account.comment_count,
                                account.retweet_count + account.quote_count,
                                account.engagement,
                                account.impression_count,
                            )
                        ],
                        start_date=start_date,
                        end_date=end_date,
                    )
                    continue
                response = account._get_users_tweets()
                for val_x in response.data or []:
                    public_metrics = account._get_public_metrics(val_x)
                    like_count += public_metrics[0]
                    impression_count += public_metrics[1]
                    comment_count += public_metrics[2]
                    retweet_count += public_metrics[3]
                    quote_count += public_metrics[4]
                update_account_data.update(
                    {
                        "like_count": like_count,
                        "impression_count": impression_count,
                        "retweet_count": retweet_count,
                        "quote_count": quote_count,
                        "comment_count": comment_count,
                        "last_post_id": response.meta.get("newest_id", False)
                        if account.enable_since
                        else False,
                    }
                )
                account.write(update_account_data)
            except TooManyRequests as exManyRequest:
                account._get_message_many_requests(
                    exManyRequest, endpoint="chart_account", view_type="chart"
                )
            except Exception as e:
                _logger.exception("Error reading the statistics of the X account")
                self._notify_user_client(
                    notif_type="social_chart_danger",
                    notif_message=str(e),
                    media="X",
                    account_name=account.name,
                )
            data_x += account._map_chart_statistics(
                [
                    (
                        0,
                        account.like_count,
                        account.comment_count,
                        account.retweet_count + account.quote_count,
                        account.engagement,
                        account.impression_count,
                    )
                ],
                start_date=start_date,
                end_date=end_date,
            )
        return list(itertools.chain(data, data_x))
