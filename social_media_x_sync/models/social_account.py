# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import pytz
from tweepy.errors import Forbidden, TooManyRequests, Unauthorized

from odoo import api, fields, models

from odoo.addons.social_media_x.social_x_utils import _URL_X

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """Import into Odoo what an X account already published."""

    _inherit = "social.account"

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

    def _get_x_statistics(self, statistics):
        return self._media_statistics_payload("x", statistics)

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

    def _get_timeline_account_values(self, response, post_accounts):
        """Return the values to write on the account after reading its timeline.

        The publications of the page and the checkpoint of the timeline, and
        no aggregated figure: every tweet carries its own counters on its
        ``social.post.account``, and the figures of the account are derived
        from those rows by ``social_media_base``.

        :param response: answer of the timeline endpoint.
        :param post_accounts: commands building the publications of the page.
        :rtype: dict
        """
        self.ensure_one()
        values = {}
        if post_accounts:
            values["post_account_ids"] = post_accounts
        values["last_post_ref"] = (
            response.meta.get("newest_id", False) if self.enable_since else False
        )
        return values

    def _update_posts_statistics(self, post_id, domain, imported=None):
        statistics = super()._update_posts_statistics(post_id, domain, imported)
        PostAccount = self.env["social.post.account"]
        account_ids = self._accounts_of_media("x")
        if self and not account_ids:
            # Asked for accounts, none of them X's: nothing to read, and the
            # payload is the one the other connectors already filled.
            return self._get_x_statistics(statistics)

        for account in account_ids:
            try:
                result = account._valid_time_request(endpoint="get_tweets")
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
                        if not response.errors:
                            # X answering that nothing was published since the
                            # checkpoint is a good read with nothing to bring
                            # in, unlike a page it refused.
                            account._report_imported(imported)
                        continue
                    media_map = {
                        m.media_key: (m.media_key, m.url, m.type)
                        for m in (response.includes.get("media") or [])
                    }
                    post_accounts_by_tweet = PostAccount._by_remote_ref(
                        [str(val_x.id) for val_x in (response.data or []) if val_x.id],
                        account,
                        sudo=True,
                        active_test=False,
                    )
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
                            media_refs = {}
                            if media_keys:
                                (
                                    image_ids,
                                    media_refs,
                                ) = post_account._get_assets_save_x(
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
                            data = {
                                "remote_ref": val_x.get("id"),
                                "post_account_url": (
                                    f"{_URL_X}{account.username}/status/{val_x.id}"
                                ),
                                "message": message_text,
                                "account_id": account.id,
                                # ``created_at`` comes with its offset and
                                # ``published_date`` is stored in UTC, which
                                # is what the client converts for the reader.
                                "published_date": val_x.created_at.astimezone(
                                    pytz.utc
                                ).replace(tzinfo=None),
                                **account._x_statistics_values(public_metrics),
                                "actor_urn": val_x.author_id,
                                "state": "posted",
                                "author": author.username,
                            }
                            post_accounts.append(
                                account._import_command(
                                    post_account, data, image_ids, media_refs
                                )
                            )
                    account.write(
                        account._get_timeline_account_values(
                            response,
                            post_accounts,
                        )
                    )
                    account._report_imported(imported)

            except TooManyRequests as exManyRequest:
                account._get_message_many_requests(
                    ex=exManyRequest, endpoint="get_tweets"
                )
            except (Unauthorized, Forbidden) as error:
                account._flag_credentials_expired(str(error))
            except Exception as e:  # noqa: BLE001 - tweepy may fail in any way
                _logger.exception("Error reading the posts of the X account")
                self._notify_user_client(
                    notif_type="social_kanban_danger",
                    notif_message=str(e),
                    media="X",
                    account_name=account.name,
                )
        return self._get_x_statistics(statistics)

    def _x_check_updates(self):
        """Import what these X accounts published since the last pass.

        X has no cheap answer to *did anything move*: the only endpoint that
        knows is the timeline, and reading it is already the import. So this
        check does not flag the account for the user to import later, it
        imports, and what it answers is whether it ran.

        Each account in its own savepoint: the import writes as it goes, so a
        failure on one must not undo what the previous ones already imported nor
        stop the ones still to come. The concurrency error is re-raised on
        purpose, so Odoo still retries the cron.

        :return: whether new updates were found.
        :rtype: bool
        """
        update = super()._x_check_updates()
        for account in self:
            imported = set()
            with account._account_guard(
                "Error importing the posts of the X account %s"
            ):
                account._update_posts_statistics(None, None, imported)
                if imported:
                    update = True
        return update
