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
from tweepy.errors import TooManyRequests

from odoo import api, fields, models

from ..social_x_utils import _get_oauth

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    _inherit = "social.account"

    x_access_token_oauth2 = fields.Char(string="Token for read", help="Read tweets")
    x_access_token_oauth1 = fields.Char(
        string="Token for write", help="Post, like, comment, answer"
    )
    x_access_secret_oauth1 = fields.Char()
    x_api_key = fields.Char(string="API Key")
    x_api_secret = fields.Char(string="API Secret")
    x_account_id = fields.Char()
    retweet_count = fields.Integer(default=0)
    quote_count = fields.Integer(default=0)
    rate_limit_endpoint = fields.Json(copy=False, default=dict)
    last_post_id = fields.Char()
    enable_since = fields.Boolean(
        default=False,
        help="""This field defines the post from which to
                start filtering in the next search. This is useful
                considering the limitations of the API in its FREE version.
                It also has the disadvantage that metrics for previous posts
                will not be updated if this option is selected.
              """,
    )
    post_since_id = fields.Many2one(
        "social.post.account",
        compute="_compute_post_since_id",
        store=True,
        domain=[("media_type", "=", "x")],
        help="This post is updated with each request with the latest one.",
    )
    engagement = fields.Float(default=0, compute="_compute_engagement", store=True)

    @api.depends("interactions_count", "impression_count")
    def _compute_engagement(self):
        for account in self:
            if account.media_type == "x":
                account.engagement = (
                    account.interactions_count / (account.impression_count * 100)
                    if account.impression_count > 0
                    else 0
                )

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

    @api.depends("last_post_id")
    def _compute_post_since_id(self):
        SocialPostAccount = self.env["social.post.account"]
        for account in self:
            if not account.enable_since:
                continue
            domain = [("account_id", "=", account.id)]
            if account.last_post_id:
                domain.append(("x_post_account_id", "=", account.last_post_id))
            account.post_since_id = SocialPostAccount.search(
                domain, limit=1, order="published_date desc"
            ).id

    def _get_group_account_username(self):
        account_repeat = self.read_group(
            domain=[("id", "in", self.ids)], fields=["username"], groupby=["username"]
        )
        return account_repeat

    def _fields_account_url(self):
        return super()._fields_account_url() + [
            (
                "x_account_id",
                f"https://x.com/{self.username}",
            )
        ]

    def _valid_time_request(self, endpoint="get_tweets"):
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
        timezone = pytz.timezone(self.env.user.tz or "UTC")
        if ex:
            headers = ex.response.headers
            rate_limit_endpoint = dict(self.rate_limit_endpoint or {})
            rate_limit_endpoint[endpoint] = {
                # Limit of requests per window
                "x-rate-limit-limit": int(headers.get("x-rate-limit-limit", 0)),
                # Remaining amount for the current window
                "x-rate-limit-remaining": int(headers.get("x-rate-limit-remaining", 0)),
                # Date the window is reset and the x-rate-limit-limit is restored
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
        message = self.env._(
            """You have reached the limit of requests
            <b>%(endpoint)s</b> allowed according to your account plan.
            <br>\u2022\u2009<b>Total limit:</b> %(limit)s request(s)
            per window or period
            <br>\u2022\u2009<b>Remaining:</b> %(remaining)s
            <br>\u2022\u2009<b>Next request:</b> %(next_request)s<br>
            Please try again after that time (Next request).<br>
            For more information, see the
            <a href='%(rate_limit_url)s' target='_blank'>rate limits</a>.
        """
        ) % {
            "limit": self.rate_limit_endpoint.get(endpoint, {}).get(
                "x-rate-limit-limit", 0
            ),
            "remaining": self.rate_limit_endpoint.get(endpoint, {}).get(
                "x-rate-limit-remaining", 0
            ),
            "next_request": next_valid_request,
            "endpoint": endpoint.replace("_", " ").capitalize(),
            "rate_limit_url": "https://docs.x.com/x-api/fundamentals/rate-limits",
        }
        _logger.info(message)
        self._notify_user_client(
            notif_type=f"social_{view_type}_info",
            notif_message=message,
            media="X",
            account_name=self.name,
        )
        return False

    def _get_access_token_oauth2(self, wizard_social_account=None):
        credentials = (
            f"{wizard_social_account.x_api_key or self.x_api_key}:"
            f"{wizard_social_account.x_api_secret or self.x_api_secret}"
        ).encode()
        b64_credentials = base64.b64encode(credentials).decode("utf-8")
        url = "https://api.twitter.com/oauth2/token"
        headers = {
            "Authorization": f"Basic {b64_credentials}",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        }
        data = {"grant_type": "client_credentials"}
        response = requests.post(url, headers=headers, data=data, timeout=10)
        token = response.json().get("access_token", False)
        return token

    def _get_access_token(self, kwargs):
        url = "https://api.twitter.com/oauth/access_token"
        wizard_social_account = (
            self.env["wizard.social.account"]
            .sudo()
            .search([("oauth_token", "=", kwargs.get("oauth_token", False))], limit=1)
        )
        auth = _get_oauth(
            wizard_social_account.x_api_key or self.x_api_key,
            wizard_social_account.x_api_secret or self.x_api_secret,
            request_access_token=kwargs,
        )
        oauth_verifier = kwargs.get("oauth_verifier")
        response = requests.post(
            url, auth=auth, data={"oauth_verifier": oauth_verifier}, timeout=10
        )
        access_tokens = dict(x.split("=") for x in response.text.split("&"))
        access_token = access_tokens["oauth_token"]
        access_token_secret = access_tokens["oauth_token_secret"]
        return access_token, access_token_secret

    def get_client_api(
        self,
        client_api=True,
        x_access_token_oauth1=None,
        x_access_secret_oauth1=None,
        bearer_token=None,
        kwargs=None,
    ):
        if client_api:
            wizard_social_account = None
            if kwargs:
                wizard_social_account = (
                    self.env["wizard.social.account"]
                    .sudo()
                    .search_fetch(
                        [("oauth_token", "=", kwargs.get("oauth_token", False))],
                        ["x_api_key", "x_api_secret"],
                        limit=1,
                    )
                )
            return tweepy.Client(
                bearer_token=self.x_access_token_oauth2 or bearer_token,
                consumer_key=self.x_api_key or wizard_social_account.x_api_key,
                consumer_secret=self.x_api_secret or wizard_social_account.x_api_secret,
                access_token=x_access_token_oauth1 or self.x_access_token_oauth1,
                access_token_secret=self.x_access_secret_oauth1
                or x_access_secret_oauth1
                or self.x_access_secret_oauth1,
            )
        auth = tweepy.OAuth1UserHandler(
            consumer_key=self.x_api_key,
            consumer_secret=self.x_api_secret,
            access_token=x_access_token_oauth1 or self.x_access_token_oauth1,
            access_token_secret=x_access_secret_oauth1 or self.x_access_secret_oauth1,
        )
        return tweepy.API(auth)

    def _update_account_data(self):
        client = self.get_client_api(bearer_token=self.x_access_token_oauth2)
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
                wizard_social_account = (
                    self.env["wizard.social.account"]
                    .sudo()
                    .search_fetch(
                        [("oauth_token", "=", kwargs.get("oauth_token", False))],
                        ["x_api_key", "x_api_secret"],
                        limit=1,
                    )
                )
                media_content = requests.get(data.profile_image_url, timeout=10)
                account_image = None
                if media_content.status_code == 200:
                    account_image = base64.b64encode(media_content.content)
                values = {
                    "x_account_id": data.id,
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
                    acc_count = (
                        self.env["social.account"]
                        .sudo()
                        .search(
                            [
                                ("media_type", "=", "x"),
                                ("username", "=", data.username),
                            ],
                            limit=1,
                        )
                    )
                    if not acc_count:
                        self.create(values)
                    else:
                        acc_count.write(values)
                else:
                    message_error = "Not create account: Not get access token OAuth2"
                    self._notify_user_client(
                        notif_type="social_kanban_danger",
                        notif_message=message_error,
                        media="X",
                        account_name=self.name,
                    )
        except TooManyRequests as exManyRequest:
            self._get_message_many_requests(exManyRequest, endpoint="create_account")
        except Exception as e:
            message_error = f"Request Client Me: {e}"
            self._notify_user_client(
                notif_type="social_kanban_danger",
                notif_message=message_error,
                media="X",
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
            if not context.get("social_post_cron", False):
                self._notify_user_client(
                    notif_type="social_form_danger",
                    notif_message=ex,
                    account_name=self.name,
                    media=self.media_type,
                )
            else:
                post_id._message_error_post(str(ex), post_account_id.media_type)
            return False

    def _get_statistics(self, statistics):
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
        client_api = self.get_client_api(bearer_token=self.x_access_token_oauth2)
        return client_api.get_users_tweets(
            id=self.x_account_id,
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
        public_metrics = val_x.public_metrics
        return (
            public_metrics.get("like_count", 0),
            public_metrics.get("impression_count", 0),
            public_metrics.get("reply_count", 0),
            public_metrics.get("retweet_count", 0),
            public_metrics.get("quote_count", 0),
        )

    def _update_posts_statistics(self, post_id, domain):
        statistics = super()._update_posts_statistics(post_id, domain)
        PostAccount = self.env["social.post.account"]
        if not self:
            account_ids = self.search(
                [
                    ("media_type", "=", "x"),
                ],
            )
        elif any(val.media_type == "x" for val in self):
            account_ids = self
        else:
            return self._get_statistics(statistics)

        timezone = pytz.timezone(self.env.user.tz or "UTC")
        for account in account_ids:
            try:
                result = account.with_context(notify_client=True)._valid_time_request()
                if result:
                    post_accounts = []
                    since_id = (
                        account.post_since_id.x_post_account_id
                        if account.post_since_id
                        and account.post_since_id.x_post_account_id
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
                        _logger.error(f"Get Tweets: {message_error}")
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
                            post_account = PostAccount.search(
                                [("x_post_account_id", "=", val_x.id)], limit=1
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
                                "x_post_account_id": val_x.get("id"),
                                "post_account_url": f"https://x.com/{account.username}/status/{val_x.id}",
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
                                post_accounts.append((0, 0, data))
                            else:
                                post_accounts.append((1, post_account.id, data))
                    update_account_data = {}
                    if len(post_accounts) > 0:
                        update_account_data.update({"post_account_ids": post_accounts})
                    update_account_data.update(
                        {
                            "like_count": like_count,
                            "impression_count": impression_count,
                            "retweet_count": impression_count,
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
                self._notify_user_client(
                    notif_type="social_kanban_danger",
                    notif_message=e,
                    media="X",
                    account_name=account.name,
                )
        return self._get_statistics(statistics)

    def update_account(self):
        res = super().update_account()
        if self.media_type == "x":
            ctx = dict(res.get("context", {}))
            ctx.update(
                {
                    "default_x_api_key": self.x_api_key,
                    "default_x_api_secret": self.x_api_secret,
                }
            )
            res["context"] = ctx
        return res

    def _get_chart_account_statistics(self, start_date, end_date, granularity):
        data = super()._get_chart_account_statistics(start_date, end_date, granularity)
        data_x = []
        account_ids = self or self.search([("media_type", "=", "x")])
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
                        "retweet_count": impression_count,
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
                self._notify_user_client(
                    notif_type="social_chart_danger",
                    notif_message=e,
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
                **{"start_date": start_date, "end_date": end_date},
            )
        return list(itertools.chain(data, data_x))