# Copyright 2026 Binhex <https://www.binhex.cloud>
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
from requests_oauthlib import OAuth1
from tweepy.errors import Forbidden, TooManyRequests, Unauthorized

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_x_utils import (
    _URL_OAUTH2_TOKEN_X,
    _URL_OAUTH_X,
    _URL_PRICING_X,
    _URL_RATE_LIMITS_X,
    _URL_X,
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
    rate_limit_endpoint = fields.Json(copy=False, default=dict)
    last_post_ref = fields.Char(
        string="Last Post",
        copy=False,
        help="Reference of the newest tweet read from X, used to ask only "
        "for the ones published after it.",
    )
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

    @api.onchange("enable_since")
    def _onchange_post_since_id(self):
        for account in self:
            if not account.enable_since:
                account.post_since_id = False
                account.last_post_ref = False

    @api.depends(
        "last_post_ref",
        "enable_since",
        "post_account_ids.remote_ref",
        "post_account_ids.published_date",
    )
    def _compute_post_since_id(self):
        SocialPostAccount = self.env["social.post.account"]
        accounts = self.filtered("enable_since")
        (self - accounts).post_since_id = False
        if not accounts:
            return
        # The publications of the whole batch are read in a single query,
        # ordered so the first one found per account is the one a search
        # with ``limit=1`` would have returned.
        latest_by_account = {}
        latest_by_ref = {}
        for post_account in SocialPostAccount.search(
            [("account_id", "in", accounts.ids)], order="published_date desc"
        ):
            latest_by_account.setdefault(post_account.account_id.id, post_account.id)
            latest_by_ref.setdefault(
                (post_account.account_id.id, post_account.remote_ref), post_account.id
            )
        for account in accounts:
            if account.last_post_ref:
                account.post_since_id = latest_by_ref.get(
                    (account.id, account.last_post_ref), False
                )
            else:
                account.post_since_id = latest_by_account.get(account.id, False)

    def _get_group_account_username(self):
        """Group these accounts by username to detect duplicated X users.

        Only the X accounts already holding a username are grouped: the
        constraint calling it receives every account of the post, and neither
        the accounts of another media nor the ones whose username is still
        empty are a duplicate of anything.

        :return: Tuples of username and number of accounts using it.
        :rtype: list
        """
        return self._read_group(
            domain=[
                ("id", "in", self.ids),
                ("media_type", "=", "x"),
                ("username", "!=", False),
            ],
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
        message = Markup(
            _(
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
        _logger.info(
            "X rate limit reached on endpoint %s for account %s, next request at %s",
            endpoint,
            self.name,
            next_valid_request,
        )
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
                pricing_link = str(
                    Markup("<a href='%s' target='_blank'>%s</a>")
                    % (_URL_PRICING_X, _("X API pricing"))
                )
            return Markup(
                _(
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
                _(
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
                _(
                    "Invalid X request token. Please restart the account "
                    "association process."
                )
            )
        return wizard_social_account

    def _get_access_token(self, kwargs):
        url = f"{_URL_OAUTH_X}/access_token"
        wizard_social_account = self._get_x_oauth_wizard(kwargs)
        account_sudo = self.sudo()
        auth = OAuth1(
            wizard_social_account.x_api_key or account_sudo.x_api_key,
            wizard_social_account.x_api_secret or account_sudo.x_api_secret,
            kwargs.get("oauth_token"),
            kwargs.get("oauth_token_secret"),
        )
        oauth_verifier = kwargs.get("oauth_verifier")
        response = requests.post(
            url, auth=auth, data={"oauth_verifier": oauth_verifier}, timeout=10
        )
        if response.status_code != 200:
            raise UserError(
                _("Error getting X access token: %(error)s", error=response.text)
            )
        try:
            access_tokens = dict(x.split("=") for x in response.text.split("&"))
            return access_tokens["oauth_token"], access_tokens["oauth_token_secret"]
        except (ValueError, KeyError) as ex:
            raise UserError(
                _("Unexpected response from X: %(error)s", error=response.text)
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
                        account = self.sudo().create(
                            dict(values, user_id=self.env.user.id)
                        )
                    else:
                        if not acc_count.active:
                            values["active"] = True
                        acc_count.sudo().write(values)
                        account = acc_count
                    account._trigger_initial_sync()
                else:
                    message_error = _(
                        "The account was not created: the OAuth2 access "
                        "token could not be obtained."
                    )
                    self._notify_failed_association(message_error)
                    _logger.error(
                        "The X account was not created: no OAuth2 access token"
                    )
        except (AccessError, UserError):
            raise
        except TooManyRequests as exManyRequest:
            self._get_message_many_requests(exManyRequest, endpoint="create_account")
        except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
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

    def _prepare_medias_for_tweet(self, image_ids=None, video_ids=None):
        media_ids = []
        api = self.get_client_api(client_api=False)
        for media_post in list(itertools.chain(image_ids or [], video_ids or [])):
            image_file = io.BytesIO(base64.b64decode(media_post.datas))
            media = api.media_upload(
                filename=media_post.name or False,
                file=image_file,
            )
            media_ids.append(media.media_id)
        return media_ids

    def create_tweet(self, message, image_ids, video_ids, post_id, post_account_id):
        """Publish a post with its media.

        The rate limit is answered here, because it is not a failure of the
        post but a time to wait, and the user is told when to try again.
        Everything else is left to the caller: the publication guard records
        it on the line, with its reason, which is where the user looks for it
        afterwards. An authorization refused by X is raised as a credentials
        error, and since X has no way to renew the token from Odoo, the
        account is flagged for the user to authorize it again.

        :return: The id of the published tweet or False.
        :rtype: str | bool
        """
        context = dict(self.env.context)
        client_api = self.get_client_api()
        try:
            medias = self._prepare_medias_for_tweet(
                image_ids=image_ids, video_ids=video_ids
            )
            tweet = client_api.create_tweet(
                text=message, media_ids=medias if len(medias) > 0 else None
            )
            return tweet.data.get("id", False)
        except TooManyRequests as exManyRequest:
            if not context.get("social_post_cron", False):
                self._get_message_many_requests(
                    exManyRequest, endpoint="create_tweet", view_type="form"
                )
            else:
                post_id._message_error_post(
                    str(exManyRequest), post_account_id.media_type
                )
            return False
        except (Unauthorized, Forbidden) as error:
            raise SocialCredentialsError(
                _("PUBLISHING ON X: %(error)s", error=error)
            ) from error

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
        return public_metrics.get("like_count", 0), public_metrics.get(
            "impression_count", 0
        ), public_metrics.get("reply_count", 0), public_metrics.get(
            "retweet_count", 0
        ), public_metrics.get("quote_count", 0)

    def _get_post_accounts_by_tweet(self, tweet_ids):
        """Prefetch post accounts by tweet id to avoid per-tweet searches."""
        post_accounts_by_tweet = {}
        if tweet_ids:
            for existing in self.env["social.post.account"].search(
                [("remote_ref", "in", tweet_ids)]
            ):
                post_accounts_by_tweet.setdefault(existing.remote_ref, existing)
        return post_accounts_by_tweet

    def _notify_tweets_error(self, account, errors):
        """Report the errors X answered instead of a timeline.

        An empty page without errors is the normal answer when nothing was
        published since ``since_id``, so it is not reported at all.
        """
        if not errors:
            return
        message_error = "<br>".join(
            [f"<br>{error.get('detail', '')}" for error in errors]
        )
        _logger.error("Get Tweets: %s", message_error)
        self._notify_user_client(
            notif_type="social_kanban_danger",
            notif_message=message_error,
            media="X",
            account_name=account.name,
        )

    def _get_timeline_account_values(
        self, response, since_id, post_accounts, statistics
    ):
        """Return the values to write on the account after reading its timeline.

        :param response: answer of the timeline endpoint.
        :param since_id: publication the timeline was read from, if any.
        :param post_accounts: commands building the publications of the page.
        :param statistics: counters aggregated over the page.
        :rtype: dict
        """
        self.ensure_one()
        values = {}
        if post_accounts:
            values["post_account_ids"] = post_accounts
        if since_id is None:
            # A page read from ``since_id`` only carries the newest
            # publications, so aggregating it would replace the totals of the
            # account with a subset of them.
            values.update(statistics)
        values["last_post_ref"] = (
            response.meta.get("newest_id", False) if self.enable_since else False
        )
        return values

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
                        self._notify_tweets_error(account, response.errors)
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
                    account.write(
                        account._get_timeline_account_values(
                            response,
                            since_id,
                            post_accounts,
                            {
                                "like_count": like_count,
                                "impression_count": impression_count,
                                "retweet_count": retweet_count,
                                "quote_count": quote_count,
                                "comment_count": comment_count,
                            },
                        )
                    )

            except TooManyRequests as exManyRequest:
                account.with_context(notify_client=True)._get_message_many_requests(
                    ex=exManyRequest
                )
            except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
                _logger.exception("Error reading the posts of the X account")
                self._notify_user_client(
                    notif_type="social_kanban_danger",
                    notif_message=str(e),
                    media="X",
                    account_name=account.name,
                )
        return self._get_x_statistics(statistics)

    def action_update_account(self):
        res = super().action_update_account()
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
