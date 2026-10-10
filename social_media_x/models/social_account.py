# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
import logging
import time
from datetime import datetime
from urllib.parse import parse_qsl

import pytz
import requests
import tweepy
from markupsafe import Markup, escape
from requests_oauthlib import OAuth1
from tweepy.errors import BadRequest, Forbidden, TooManyRequests, Unauthorized

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare, float_is_zero, split_every

from odoo.addons.social_media_base.exceptions import SocialCredentialsError

from ..social_x_utils import (
    _GET_POSTS_MAX_IDS_X,
    _MAX_MESSAGE_LENGTH_PREMIUM_X,
    _MAX_MESSAGE_LENGTH_X,
    _POST_FIELDS_METRICS_X,
    _URL_OAUTH2_TOKEN_X,
    _URL_OAUTH_X,
    _URL_PRICING_X,
    _URL_RATE_LIMITS_X,
    _URL_USAGE_CREDITS_X,
    _URL_X,
    _is_app_without_paid_plan,
)

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """X implementation of the social account API calls."""

    _inherit = "social.account"

    x_access_token_oauth2 = fields.Char(
        string="Token for read",
        help="App-only bearer token, obtained from the API Key and the API "
        "Secret. It authorizes what is asked in the name of the App and not "
        "of a user.",
        groups="base.group_system",
    )
    x_access_token_oauth1 = fields.Char(
        string="Token for write",
        help="Post and delete",
        groups="base.group_system",
    )
    x_access_secret_oauth1 = fields.Char(groups="base.group_system")
    x_api_key = fields.Char(
        string="API Key",
        groups="base.group_system",
        help=(
            "The API Key of the developer App, which the X Developer Console "
            "lists under OAuth 1.0 Keys as the Consumer Key. Regenerating it "
            "in the Console invalidates the one stored here."
        ),
    )
    x_api_secret = fields.Char(
        string="API Secret",
        groups="base.group_system",
        help=(
            "The API Key Secret of the developer App, shown by the X Developer "
            "Console only when the Consumer Key is generated. Regenerating it "
            "in the Console invalidates the one stored here."
        ),
    )
    x_premium = fields.Boolean(
        default=False,
        readonly=True,
        copy=False,
        help="Whether the X user of this account holds an X Premium "
        "subscription, which raises the message of a post from 280 to 25 000 "
        "characters. Read from X when the account is associated and on Update "
        "account, so a subscription bought or cancelled later is seen after "
        "pressing Update account.",
    )
    x_credit_balance = fields.Float(
        string="Credit Balance (USD)",
        digits=(16, 2),
        readonly=True,
        copy=False,
        help="What is left of the credits the developer App bought to pay "
        "for the calls to the X API. It is the balance of the App and not of "
        "this account, so the accounts holding the same API Key share it. It "
        "is read again every 2 hours and when the account is associated, "
        "updated or its statistics refreshed.",
    )
    x_credit_balance_date = fields.Datetime(
        string="Credit Balance Read On",
        readonly=True,
        copy=False,
        help="When X last answered the credit balance.",
    )
    x_credit_warning = fields.Float(
        string="Credit Warning (USD)",
        digits=(16, 2),
        default=1.0,
        help="The responsible of the account is warned when the credit "
        "balance drops under this amount. At 0, only when it is used up.",
    )
    x_credit_warned = fields.Boolean(
        readonly=True,
        copy=False,
        help="Whether the responsible was already warned that the credit "
        "balance is under the warning threshold. Cleared when the balance is "
        "read again at or over it, so the warning is given once per drop.",
    )
    rate_limit_endpoint = fields.Json(copy=False, default=dict)

    def _get_group_account_username(self):
        """Return the usernames more than one of these accounts holds.

        Only the X accounts already holding a username are grouped: the
        constraint calling it receives every account of the post, and neither
        the accounts of another media nor the ones whose username is still
        empty are a duplicate of anything.

        :return: Tuples of duplicated username and number of accounts using it.
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
            having=[("__count", ">", 1)],
        )

    def _get_x_max_message_length(self):
        """Return the characters this account may publish in one post.

        The plan belongs to the account and not to the social media, so the
        limit is answered here and never read from the constants directly.

        :rtype: int
        """
        self.ensure_one()
        return (
            _MAX_MESSAGE_LENGTH_PREMIUM_X if self.x_premium else _MAX_MESSAGE_LENGTH_X
        )

    def _fields_account_url(self):
        return {**super()._fields_account_url(), "x": f"{_URL_X}{self.username}"}

    def _valid_time_request(self, endpoint):
        """Return whether the rate limit window of the endpoint is already over.

        :param endpoint: key of the endpoint about to be asked. Named by every
            caller, because the quota of X is counted per endpoint and each
            module knows only the ones it calls.
        :rtype: bool
        """
        limit_reset = (
            self.rate_limit_endpoint.get(endpoint, {}).get("x-rate-limit-reset", False)
            if self.rate_limit_endpoint
            else None
        )
        if limit_reset and limit_reset >= time.time():
            return self._get_message_many_requests(endpoint=endpoint)
        return True

    def _get_message_many_requests(self, ex=None, *, endpoint, view_type="kanban"):
        """Store the rate limit headers and tell the user when to retry.

        :param ex: the TooManyRequests error carrying the headers, if any.
        :param endpoint: key of the endpoint that answered the limit. Named by
            every caller, because the quota of X is counted per endpoint and
            each module knows only the ones it calls.

        Called from the client, from the crons and from the association, so
        the channel is left to ``_notify_user()``: the callback of X answers
        with a redirect that a message on the bus never outruns.

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
        self._notify_user(
            notif_type=f"social_{view_type}_info",
            notif_message=message,
            media="X",
            account_name=self.name,
        )
        return False

    def _get_access_token_oauth2(self, wizard_social_account=None):
        """Return the app-only bearer token X answers to the App credentials.

        It authorizes what is asked in the name of the App instead of a user,
        which is what the endpoints that only read need.
        """
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

    def _x_refresh_credit_balance(self):
        """Read the credit balance of the developer App of these accounts.

        The balance belongs to the App that pays the calls and not to the
        account, so X is asked once per API Key and the answer is written on
        every account holding it. Each API Key in its own savepoint: a group
        that fails must not undo what was written for the previous ones.

        The accounts are read and written with ``sudo()``: the API Key is
        restricted to the administrators, and an API Key may be shared with
        the accounts of another responsible, whose balance is the same one.
        The accounts of any other social media are left out.
        """
        accounts_x = self.sudo().filtered(lambda account: account.media_type == "x")
        for accounts in accounts_x.grouped("x_api_key").values():
            with accounts[0]._account_guard(
                "Error reading the X API credit balance of the account %s"
            ):
                accounts._x_write_credit_balance()

    def _x_write_credit_balance(self):
        """Ask X for the credit balance of these accounts and write it.

        Every account here holds the same API Key, so the bearer of the first
        one answers for all of them.

        The balance is only something to look at, so a failure to read it is
        logged and nothing else: it never hides what the user was doing, the
        previous balance stays and its date tells how old it is. The rate
        limit is kept in silence for the same reason, on every account of the
        API Key, since X counts it for the App and not for the account.
        """
        first_account = self[0]
        limit_reset = (
            (first_account.rate_limit_endpoint or {})
            .get("usage_credits", {})
            .get("x-rate-limit-reset", 0)
        )
        if limit_reset >= time.time():
            _logger.info(
                "X credit balance not read for account %s: rate limit until %s",
                first_account.id,
                limit_reset,
            )
            return
        try:
            response = requests.get(
                _URL_USAGE_CREDITS_X,
                headers={
                    "Authorization": f"Bearer {first_account.x_access_token_oauth2}"
                },
                timeout=10,
            )
            if response.status_code == 429:
                self._x_store_credit_rate_limit(response.headers)
                return
            if response.status_code != 200:
                _logger.warning(
                    "X refused the credit balance of account %s: %s %s",
                    first_account.id,
                    response.status_code,
                    response.text,
                )
                return
            balance = response.json()["data"]["total_balance"]
        except (requests.RequestException, ValueError, KeyError, TypeError) as error:
            _logger.warning(
                "Could not read the X credit balance of account %s: %s",
                first_account.id,
                error,
            )
            return
        previous_balances = {
            account: account.x_credit_balance if account.x_credit_balance_date else None
            for account in self
        }
        self.write(
            {
                "x_credit_balance": balance,
                "x_credit_balance_date": fields.Datetime.now(),
            }
        )
        for account in self:
            account._x_warn_credit_balance(previous_balances[account])

    def _x_warn_credit_balance(self, previous_balance):
        """Warn the responsible when the credit balance has just gone down.

        Read every 2 hours, the balance would repeat the same warning all day,
        so it is given only when the balance crosses the line. Used up, when
        it reaches 0 coming from more or from never having been read. Low,
        when it is under the warning threshold of the account and the
        responsible was not warned of it yet; reading it again at or over the
        threshold clears that, so the next drop warns again. Raising the
        threshold over the balance is a drop as well.

        The warning goes to the chatter of the account, which keeps it for a
        responsible who is not connected when the cron reads the balance, and
        to the bus, for the one who is. Read while answering the OAuth
        callback, the warning of the user who is associating the account is
        kept in the session instead, since the redirect of the callback would
        outrun the bus; the responsibles of the other accounts holding the
        same API Key are not the ones reloading, so they keep the bus.

        :param previous_balance: the balance before this read, ``None`` when
            it had never been read.
        """
        self.ensure_one()
        balance = self.x_credit_balance
        used_up = float_is_zero(balance, precision_digits=2)
        below = used_up or (
            float_compare(balance, self.x_credit_warning, precision_digits=2) < 0
        )
        message = notif_type = None
        if used_up:
            if previous_balance is None or not float_is_zero(
                previous_balance, precision_digits=2
            ):
                notif_type = "social_form_danger"
                message = _(
                    "The X API credit balance of this App is used up. X blocks "
                    "every call until credits are bought in the Developer Console."
                )
        elif below and not self.x_credit_warned:
            notif_type = "social_form_info"
            # Formatted apart: an f-string among the arguments of ``_()``
            # stops the extraction of the terms that follow it.
            balance_text = f"{balance:.2f}"
            threshold_text = f"{self.x_credit_warning:.2f}"
            message = _(
                "The X API credit balance of this App is down to USD "
                "%(balance)s, under the warning threshold of USD %(threshold)s.",
                balance=balance_text,
                threshold=threshold_text,
            )
        if self.x_credit_warned != below:
            self.x_credit_warned = below
        if not message:
            return
        self.message_post(body=message, partner_ids=self.user_id.partner_id.ids)
        if (
            self.env.context.get("social_media_oauth_callback")
            and self.user_id == self.env.user
        ):
            message_type, notification = self._prepare_user_notification(
                notif_type, message, media="X", account_name=self.name
            )
            self._notify_user_session(notification, message_type=message_type)
            return
        # The web client only listens to the information and the success of
        # a form, so a used up balance travels on the information type: the
        # kind of notice the payload carries keeps it red.
        self._notify_user_client(
            target=self.user_id.partner_id,
            notif_type=notif_type,
            notif_message=message,
            media="X",
            account_name=self.name,
            bus_type="social_form_info",
        )

    def _x_store_credit_rate_limit(self, headers):
        """Keep the rate limit window X answered for the credit balance.

        :param headers: the headers of the ``429`` answer of X.
        """
        window = {
            "x-rate-limit-limit": int(headers.get("x-rate-limit-limit", 0)),
            "x-rate-limit-remaining": int(headers.get("x-rate-limit-remaining", 0)),
            "x-rate-limit-reset": int(
                headers.get("x-rate-limit-reset", time.time() + 60)
            ),
        }
        for account in self:
            account.rate_limit_endpoint = {
                **(account.rate_limit_endpoint or {}),
                "usage_credits": window,
            }
        _logger.info(
            "X rate limit reached on the credit balance of accounts %s, "
            "next request at %s",
            self.ids,
            window["x-rate-limit-reset"],
        )

    @api.model
    def _x_error_message(self, error, pricing_link=None):
        """Explain the error of X, telling apart the App that cannot spend.

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
                    "X rejected the request because the developer App cannot "
                    "spend against the API. Connect the App to a Pay Per Use "
                    "project in Project Access > Manage, not the Default "
                    "project on Standard Basic, make sure the account has "
                    "credit in the Developer Console, see %(pricing_link)s, "
                    "then try again.",
                    pricing_link=pricing_link,
                )
            )
        return escape(str(error))

    def _x_refused_post_message(self, error, message):
        """Explain why X refused a post of this account.

        X answers a refused post with a ``400`` or a ``403`` that says little
        about the cause, so the reason is told from what Odoo knows. An App
        that cannot spend against the API is explained as such. A post longer
        than what X allows without a subscription, sent by an account X last
        reported as X Premium, asks to read the plan again with Update
        account, since a subscription cancelled after that read only shows up
        here. Any other refusal names the account and keeps the text of X,
        without its final full stop, since the message closes the sentence
        itself.

        The message ends on the failed publication, which stores it as plain
        text, so the link to the pricing page is written as its address.

        :param error: the ``BadRequest`` or ``Forbidden`` raised by tweepy.
        :param str message: the text of the post, as it was sent to X.
        :return: the reason to show to the user, as plain text.
        :rtype: str
        """
        self.ensure_one()
        if isinstance(error, Forbidden) and _is_app_without_paid_plan(error):
            return str(self._x_error_message(error, pricing_link=_URL_PRICING_X))
        reason = str(error).rstrip().rstrip(".")
        if self.x_premium and len(message or "") > _MAX_MESSAGE_LENGTH_X:
            return _(
                "X refused the post of %(account)s: %(error)s. What an "
                "account may publish depends on its plan, and X reported X "
                "Premium for this account when it was last read. Press Update "
                "account to read the plan again before trying again.",
                account=self.display_name,
                error=reason,
            )
        return _(
            "X refused the post of %(account)s: %(error)s.",
            account=self.display_name,
            error=reason,
        )

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
            access_tokens = dict(parse_qsl(response.text))
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

        ``client_api`` returns the API v2 client, which serves every endpoint
        of X but the upload of medias; otherwise the v1.1 client, still needed
        for that upload.

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

    def _x_download_profile_image(self, url):
        """Return the profile picture of an X account, encoded for the field.

        :param url: address X answered for the picture.
        :return: the image in base64, or ``None`` when X did not serve it.
        """
        media_content = requests.get(url, timeout=10)
        if media_content.status_code != 200:
            return None
        return base64.b64encode(media_content.content)

    def _x_premium_values(self, user):
        """Return the plan of the authorized X user as values to write.

        X answers ``subscription_type`` only for the authenticated user, as
        the text ``"None"`` when there is no subscription and as the name of
        the plan otherwise. Every plan allows long posts, so any other text
        means X Premium. tweepy keeps the field only in the raw answer, never
        as an attribute of the user.

        :param user: the ``tweepy.User`` answered by ``get_me``.
        :return: ``x_premium`` to write, or nothing when X did not answer the
            plan, so the value already stored is kept.
        :rtype: dict
        """
        raw_data = user.data if isinstance(user.data, dict) else {}
        subscription_type = raw_data.get("subscription_type")
        if not isinstance(subscription_type, str):
            return {}
        return {"x_premium": subscription_type != "None"}

    def _update_account_data(self):
        client = self.get_client_api(bearer_token=self.sudo().x_access_token_oauth2)
        data = client.get_me(
            user_fields=[
                "username",
                "name",
                "profile_image_url",
                "created_at",
                "subscription_type",
            ]
        ).data
        values = {
            "name": data.name,
            "username": data.username,
            **self._x_premium_values(data),
        }
        account_image = self._x_download_profile_image(data.profile_image_url)
        if account_image:
            values.update(
                {
                    "image_1920": account_image,
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
                    "subscription_type",
                ]
            ).data
            if data.username:
                wizard_social_account = self._get_x_oauth_wizard(kwargs)
                account_image = self._x_download_profile_image(data.profile_image_url)
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
                    "last_update_account": fields.Datetime.now(),
                    **self._x_premium_values(data),
                }
                access_token_oauth2 = self._get_access_token_oauth2(
                    wizard_social_account
                )
                if access_token_oauth2:
                    values.update({"x_access_token_oauth2": access_token_oauth2})
                    account = self._associate_account(
                        "x", str(data.id), values, username=data.username
                    )
                    # Before reading the figures: X refusing them leaves its
                    # own message, which must not hide that the account was
                    # associated.
                    self._notify_user_session(
                        self._format_user_notification(
                            _("The account was associated successfully"),
                            media="X",
                            message_type="success",
                        ),
                        message_type="success",
                    )
                    # After the success, so that a low balance is told once
                    # the user knows the account is there, and before the
                    # figures, whose failure ends the callback.
                    account._x_refresh_credit_balance()
                    account._on_account_associated()
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
        """Upload the medias of a post to X and return what it calls them.

        The ``media_id`` X answers belongs to the account that uploaded the
        file, so publishing the same image on several accounts uploads it
        once per account. Which attachment produced each one is what the
        publication stores in ``media_refs``, hence the identifier as key
        instead of the position in a list.

        :param image_ids: the images to upload.
        :param video_ids: the videos to upload.
        :return: the ``media_id`` of each media, keyed by the identifier of
            its attachment.
        :rtype: dict
        """
        media_refs = {}
        api = self.get_client_api(client_api=False)
        for media_post in [*(image_ids or []), *(video_ids or [])]:
            image_file = io.BytesIO(base64.b64decode(media_post.datas))
            media = api.media_upload(
                filename=media_post.name or False,
                file=image_file,
            )
            media_refs[str(media_post.id)] = media.media_id
        return media_refs

    def create_tweet(self, message, image_ids, video_ids, post_id, post_account_id):
        """Publish a post with its media.

        The rate limit is answered here, because it is not a failure of the
        post but a time to wait, and the user is told when to try again.
        Everything else is left to the caller: the publication guard records
        it on the line, with its reason, which is where the user looks for it
        afterwards. A ``401`` is raised as a credentials error: X answers it
        for a token it no longer accepts, and since X has no way to renew the
        token from Odoo, the account is flagged for the user to authorize it
        again.

        A ``400`` or a ``403`` is a post X refuses, not a token it rejects:
        the cause is the plan of the App, the plan of the account, the
        permissions of the App or the content, and none of them is fixed by
        authorizing the account again. They are raised as a user error with
        the reason told by :meth:`~._x_refused_post_message`, and the account
        is left as it is. The upload of the medias runs inside the same
        guard, so a media X refuses is explained the same way.

        The references of the medias travel back with the identifier of the
        tweet, so the publication stores in one write what it published and
        what X called each of its medias.

        :return: The id of the published tweet or False, and the ``media_id``
            of each media keyed by the identifier of its attachment.
        :rtype: tuple
        """
        context = dict(self.env.context)
        client_api = self.get_client_api()
        media_refs = {}
        try:
            media_refs = self._prepare_medias_for_tweet(
                image_ids=image_ids, video_ids=video_ids
            )
            tweet = client_api.create_tweet(
                text=message, media_ids=list(media_refs.values()) or None
            )
            return tweet.data.get("id", False), media_refs
        except TooManyRequests as exManyRequest:
            if not context.get("social_post_cron", False):
                self._get_message_many_requests(
                    exManyRequest, endpoint="create_tweet", view_type="form"
                )
            else:
                post_id._message_error_post(
                    str(exManyRequest), post_account_id.media_type
                )
            return False, media_refs
        except Unauthorized as error:
            raise SocialCredentialsError(
                _("PUBLISHING ON X: %(error)s", error=error)
            ) from error
        except (BadRequest, Forbidden) as error:
            raise UserError(self._x_refused_post_message(error, message)) from error

    def _run_check_media_updates(self):
        """Check the X accounts for updates on the social media.

        X renews nothing and writes no daily series here: its OAuth 1.0a token
        does not expire, so there is no credential to refresh, and the API
        reports no figures by day to rewrite. What is left of the pass is the
        accounts themselves, which are searched here and handed over to
        :meth:`~._x_check_updates` — an empty hook, because reading back what an
        account already published is the business of a synchronization module
        and not of the connector. Before handing them over, the credit balance
        of their App is read: one call per API Key, whatever the history of
        the account.

        Which accounts are checked is asked to
        :meth:`~._get_check_media_updates_domain`, so the module with a reason to
        leave one out —the one whose first import has not run yet— says so in one
        place instead of here.

        :return: whether new updates were found, by this connector or before it.
        :rtype: bool
        """
        update = super()._run_check_media_updates()
        accounts = self.sudo().search(
            self._get_check_media_updates_domain() + [("media_type", "=", "x")]
        )
        if not accounts:
            return update
        accounts._x_refresh_credit_balance()
        return accounts._x_check_updates() or update

    def _x_check_updates(self):
        """Announce that these X accounts are due for a check.

        Empty hook. Knowing whether the timeline of an X account moved means
        reading that timeline, and reading it is already the import, whose cost
        grows with the history of the account. So the connector says *these are
        the accounts* and does not care who listens. Without a synchronization
        module installed nothing listens, and that is a valid installation: the
        account is linked and can publish.

        :return: whether new updates were found.
        :rtype: bool
        """
        return False

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

    @api.model
    def _x_statistics_values(self, public_metrics):
        """Return the metrics of a post as the statistics fields holding them.

        Shared by the refresh of the figures and by the import of
        ``social_media_x_sync``: both read the same ``public_metrics`` block,
        so a second copy of this mapping is what would let them stop speaking
        the same language.

        Also gives the engagement rate of the post, which X does not report:
        its interactions over its impressions, as a ratio from 0 to 1. The
        interactions are the ones ``interactions_count`` adds for X, since X
        fills in neither clicks nor shares.

        :param public_metrics: the five figures ``_get_public_metrics`` builds.
        :rtype: dict
        """
        likes, impressions, replies, retweets, quotes = public_metrics
        interactions = likes + replies + retweets + quotes
        return {
            "like_count": likes,
            "impression_count": impressions,
            "comment_count": replies,
            "retweet_count": retweets,
            "quote_count": quotes,
            "engagement": interactions / impressions if impressions else 0,
        }

    def _get_posts_metrics(self, refs):
        """Read the public metrics of these posts, by batches of ids.

        The cheap half of what X answers about a publication: the ids are
        already known, so nothing walks the timeline and one call answers a
        hundred posts.

        Its own rate limit key, ``get_posts``: the quota of X is counted per
        endpoint, and this is neither the timeline the import reads
        (``get_tweets``) nor the single post the check for a deletion reads
        (``get_post``).

        A post missing from the answer is a post X did not report — deleted,
        or hidden — and not one whose figures are zero, so it is simply absent
        from the result and the caller leaves its line alone.

        :param refs: the identifiers of the posts to read.
        :return: the metrics tuple by post identifier, empty when the window
            of the rate limit is not over yet.
        :rtype: dict
        """
        self.ensure_one()
        metrics = {}
        if not refs or not self._valid_time_request(endpoint="get_posts"):
            return metrics
        client_api = self.get_client_api(bearer_token=self.sudo().x_access_token_oauth2)
        for batch in split_every(_GET_POSTS_MAX_IDS_X, refs, list):
            try:
                response = client_api.get_tweets(
                    ids=batch, tweet_fields=_POST_FIELDS_METRICS_X
                )
            except TooManyRequests as exManyRequest:
                # What was read before the limit is kept: the calls are spent
                # and the figures they brought are as good as the others.
                self._get_message_many_requests(exManyRequest, endpoint="get_posts")
                return metrics
            for val_x in response.data or []:
                metrics[str(val_x.id)] = self._get_public_metrics(val_x)
        return metrics

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures X reports for these publications.

        Each account in its own savepoint: the pass writes as it goes, so an
        account X refuses must neither undo what was written for the previous
        ones nor stop the ones still to come.

        :param post_accounts: the lines to read, every one with a
            ``remote_ref``.
        :return: the lines X answered for, plus whatever the other connectors
            answered for their own.
        """
        posts_x = post_accounts.filtered(lambda line: line.account_id.media_type == "x")
        refreshed = super()._refresh_post_statistics(post_accounts - posts_x)
        for account, lines in posts_x.grouped("account_id").items():
            with account._account_guard(
                "Error refreshing the statistics of the posts of the X account %s"
            ):
                refreshed |= account._write_posts_metrics(lines)
        return refreshed

    def _write_posts_metrics(self, post_accounts):
        """Ask X for these posts and write the figures it reported.

        Only the lines X answered for are written, and only they carry the
        date: a post it did not report is one whose figures could not be read,
        so its line keeps the last ones it had instead of dropping to zero.

        The lines are written with ``sudo()`` for the same reason the figures
        of the account are: they mirror what X reported and belong to the
        responsible of the account, and the *Update* button of a regular user
        has to work all the same.

        :param post_accounts: the lines of this account to read.
        :return: the lines X answered for.
        :rtype: recordset
        """
        self.ensure_one()
        metrics = self._get_posts_metrics(post_accounts.mapped("remote_ref"))
        read_on = fields.Datetime.now()
        answered = post_accounts.browse()
        for line in post_accounts:
            public_metrics = metrics.get(line.remote_ref)
            if public_metrics is None:
                continue
            line.sudo().write(
                {
                    **self._x_statistics_values(public_metrics),
                    "statistics_date": read_on,
                }
            )
            answered |= line
        return answered

    def action_refresh_statistics(self):
        """Read the credit balance of the App as well, for an X account."""
        res = super().action_refresh_statistics()
        if self.media_type == "x":
            self._x_refresh_credit_balance()
        return res

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
