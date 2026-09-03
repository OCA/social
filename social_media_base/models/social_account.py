# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging

import psycopg2
from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import file_open

from ..exceptions import SocialCredentialsError

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """Account associated with a social media."""

    _name = "social.account"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "avatar.mixin",
        "social.media.base.mixin",
        "social.statistics.mixin",
    ]
    _description = "Account Linked to a Social Media"

    @api.model
    def _default_image(self):
        with file_open("base/static/img/avatar.png", "rb") as image_file:
            return base64.b64encode(image_file.read())

    name = fields.Char()
    active = fields.Boolean(default=True)
    username = fields.Char()
    media_id = fields.Many2one("social.media", ondelete="restrict")
    media_type = fields.Selection(related="media_id.media_type")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        required=True,
        index=True,
        default=lambda self: self.env.user,
        tracking=True,
        help="User this account belongs to. Only the responsible user and the "
        "social media administrators can see it.",
    )
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this account on the social media. It is set by "
        "the connector module of each social media.",
    )
    last_update_account = fields.Datetime()
    post_account_ids = fields.One2many("social.post.account", "account_id")
    post_ids = fields.Many2many(
        "social.post",
        relation="social_account_social_post_rel",
        column1="social_account_id",
        column2="social_post_id",
        string="Posts",
        readonly=True,
        help="Posts that target this account. Inverse of the accounts of a "
        "post, it is what keeps the counter up to date.",
    )
    image_1920 = fields.Image(default=_default_image)

    engagement = fields.Float(default=0, digits=(16, 2))

    account_url = fields.Char(compute="_compute_account_url")
    need_update = fields.Boolean(default=False)
    access_token = fields.Char(groups="base.group_system")
    refresh_access_token = fields.Char(groups="base.group_system")
    expire_access_token_date = fields.Date(string="Expire Access Token")
    can_manage_account = fields.Boolean(
        compute="_compute_can_manage_account",
        help="Whether the current user may update or archive this account: "
        "its responsible user and the social media administrators.",
    )
    post_count = fields.Integer(compute="_compute_post_count")
    utm_campaign_count = fields.Integer(compute="_compute_utm_campaign_count")

    @api.depends("post_ids")
    def _compute_post_count(self):
        counts = dict(
            self.env["social.post"]._read_group(
                domain=[("account_ids", "in", self.ids)],
                groupby=["account_ids"],
                aggregates=["__count"],
            )
        )
        for account in self:
            account.post_count = counts.get(account, 0)

    def action_open_posts(self):
        """Open the posts this account is one of the targets of."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Posts"),
            "res_model": "social.post",
            "view_mode": "kanban,tree,form",
            "domain": [("account_ids", "in", self.ids)],
            "context": {"default_account_ids": [Command.set(self.ids)]},
        }

    def _get_utm_campaigns(self):
        """Return the marketing campaigns of the posts of this account.

        Both sides have to be read. A publication imported from the social
        media has no parent post and its campaign is written on the imported
        publication itself, so the posts alone would leave it out; and a post
        that is still a draft has no publication yet, so the publications
        alone would leave its campaign out until it is sent.

        :rtype: recordset
        """
        campaigns = (
            self.env["social.post.account"]
            .search(
                [
                    ("account_id", "in", self.ids),
                    ("campaign_id", "!=", False),
                ]
            )
            .campaign_id
        )
        return (
            campaigns
            | self.env["social.post"]
            .search(
                [
                    ("account_ids", "in", self.ids),
                    ("campaign_id", "!=", False),
                ]
            )
            .campaign_id
        )

    @api.depends("post_account_ids.campaign_id", "post_ids.campaign_id")
    def _compute_utm_campaign_count(self):
        for account in self:
            account.utm_campaign_count = len(account._get_utm_campaigns())

    def action_open_utm_campaigns(self):
        """Open the marketing campaigns of the publications of this account."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Marketing Campaigns"),
            "res_model": "utm.campaign",
            "view_mode": "tree,form",
            "domain": [("id", "in", self._get_utm_campaigns().ids)],
        }

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_can_manage_account(self):
        is_manager = self.env.user.has_group(
            "social_media_base.group_social_media_manager"
        )
        for account in self:
            account.can_manage_account = is_manager or account.user_id == self.env.user

    def action_update_account(self):
        return {
            "res_model": "wizard.social.account",
            "views": [[False, "form"]],
            "target": "new",
            "type": "ir.actions.act_window",
            "context": {
                "default_account_id": self.id,
                "default_media_id": self.media_id.id,
                "social_update_account": True,
            },
        }

    def action_refresh_statistics(self):
        """Ask the social media again for the figures of the last days.

        The graph view reads what the crons left, so this is what a user
        presses when he does not want to wait for the next pass. A social
        media that reports no figures by day answers nothing, and saying so
        is more useful than announcing an update that did not happen.
        """
        self.ensure_one()
        # ``media`` is what the notification is built around: without it
        # ``_format_user_notification`` answers an empty message and nothing
        # reaches the user at all.
        media = self.media_type or self.media_id.name
        if self._refresh_statistics():
            self._notify_user_client(
                notif_type="social_form_success",
                notif_message=_("The statistics of the account were updated."),
                media=media,
                account_name=self.display_name,
            )
        else:
            self._notify_user_client(
                notif_type="social_form_info",
                notif_message=_(
                    "This social media does not report statistics by day, so "
                    "there is no history to update."
                ),
                media=media,
                account_name=self.display_name,
            )

    def action_archive_account(self):
        """Archive the accounts and their whole footprint.

        Nothing is removed from the social media: relinking the account
        reactivates everything.
        """
        self.write(
            {
                "active": False,
            }
        )

    def action_unarchive_account(self):
        """Restore the accounts and everything archived with them.

        The scheduled posts whose date passed while the account was archived
        are sent back to draft instead of being published on the spot: that is
        handled by ``social.post.write`` for every way of reactivating a post,
        see :meth:`~odoo.addons.social_media_base.models.social_post.SocialPost.
        _reset_overdue_schedule`.
        """
        self.write(
            {
                "active": True,
            }
        )

    @api.model
    def _find_account_to_associate(self, media_type, remote_ref, username=None):
        """Return the account already linked to ``remote_ref`` on this media.

        The remote reference is the only immutable identifier: a user name
        can be renamed and reused by somebody else. ``username`` is a
        fallback for the accounts created before it was stored.
        """
        accounts = self.sudo().with_context(active_test=False)
        account = (
            accounts.search(
                [
                    ("media_type", "=", media_type),
                    ("remote_ref", "=", remote_ref),
                ],
                limit=1,
            )
            if remote_ref
            else self.browse()
        )
        if not account and username:
            account = accounts.search(
                [
                    ("media_type", "=", media_type),
                    ("username", "=", username),
                    ("remote_ref", "in", [False, ""]),
                ],
                limit=1,
            )
        return account

    def _check_can_associate(self):
        """Check the current user may relink this already existing account.

        Associating writes the credentials of whoever completes the OAuth
        flow, so it is restricted to the responsible user and to the
        managers to prevent taking over somebody else's account.
        """
        self.ensure_one()
        account_sudo = self.sudo()
        if (
            account_sudo.company_id
            and account_sudo.company_id not in self.env.companies
        ):
            raise AccessError(
                _(
                    "The account %(account)s belongs to another company.",
                    account=account_sudo.display_name,
                )
            )
        if self.env.user.has_group("social_media_base.group_social_media_manager"):
            return
        if account_sudo.user_id != self.env.user:
            raise AccessError(
                _(
                    "The account %(account)s is already associated with "
                    "another user. Ask its responsible user or a social "
                    "media administrator to relink it.",
                    account=account_sudo.display_name,
                )
            )

    def _on_account_associated(self):
        """Announce that these accounts were just linked.

        Empty hook. Associating an account is the business of the connector
        and importing what it already published is somebody else's, so the
        connector says *it happened* and does not care who listens. Without a
        synchronization module installed nothing listens, and that is a valid
        installation: the account is linked and can publish.
        """
        return

    def action_purge_account(self):
        """Delete the accounts and their publication history from Odoo only.

        The records of the other applications that reference an account lose
        the link instead of being deleted.

        :return: the accounts list action, the current record no longer exists.
        :rtype: dict
        """
        if not self.env.user.has_group("social_media_base.group_social_media_manager"):
            raise AccessError(
                _("Only a social media administrator can delete an account.")
            )
        accounts = self.with_context(active_test=False)
        post_accounts = accounts.post_account_ids
        linked_posts = (
            self.env["social.post"]
            .with_context(active_test=False)
            .search([("account_ids", "in", accounts.ids)])
        )
        posts = linked_posts.filtered(lambda post: not (post.account_ids - accounts))
        shared_posts = linked_posts - posts
        _logger.info(
            "%s permanently deletes the social media accounts %s",
            self.env.user.login,
            accounts.mapped("display_name"),
        )
        post_accounts.unlink()
        posts.unlink()
        if shared_posts:
            shared_posts.write(
                {"account_ids": [Command.unlink(account.id) for account in accounts]}
            )
        accounts._purge_linked_records()
        accounts.unlink()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "social_media_base.social_account_action"
        )
        action["target"] = "main"
        return action

    def _purge_linked_records(self):
        """Delete what these accounts own before they are deleted themselves.

        Extension point of :meth:`action_purge_account` for the modules
        adding records that mirror the social media of an account: the
        foreign keys only unlink them, which would leave behind records
        pointing at nothing. It runs while the accounts still exist, so the
        links can still be read.
        """

    @api.model
    def _get_removal_domain(self, media_type):
        return [("media_type", "=", media_type)]

    @api.model
    def _remove_social_media(self, media_type):
        """Drop the credentials and archive the accounts of an uninstalled media.

        ``remote_ref`` is kept, so reinstalling the connector and relinking
        the account restores its history instead of duplicating it.
        """
        accounts = (
            self.sudo()
            .with_context(active_test=False)
            .search(self._get_removal_domain(media_type))
        )
        if accounts:
            accounts.write(accounts._get_removal_values())

    def _get_removal_values(self):
        """Return the values written on an account when its module is uninstalled.

        Connector modules override it to complete these generic values.

        :rtype: dict
        """
        return {
            "access_token": False,
            "refresh_access_token": False,
            "expire_access_token_date": False,
            "active": False,
        }

    def write(self, vals):
        to_toggle = (
            self.filtered(lambda account: account.active != vals["active"])
            if "active" in vals
            else self.browse()
        )
        res = super().write(vals)
        if to_toggle:
            to_toggle._propagate_active_to_related(vals["active"])
        return res

    def _propagate_active_to_related(self, active):
        """Archive or unarchive the whole footprint of these accounts.

        Dashboard posts and the posts left without any active account. Other
        modules extend it with their own related records.
        """
        SocialPostAccount = self.env["social.post.account"].with_context(
            active_test=False
        )
        SocialPost = self.env["social.post"].with_context(active_test=False)
        SocialPostAccount.search(
            [("account_id", "in", self.ids), ("active", "!=", active)]
        ).write({"active": active})
        posts = SocialPost.search(
            [("account_ids", "in", self.ids), ("active", "!=", active)]
        )
        if not active:
            posts = posts.filtered(lambda post: not post.account_ids.filtered("active"))
        if not posts:
            return
        posts.write({"active": active})

    @api.depends("name", "media_type")
    def _compute_display_name(self):
        for account in self:
            account.display_name = (
                f"[{account.media_type.upper()}] {account.name}"
                if account.media_type
                else account.name
            )

    def _fields_account_url(self):
        """Return the account URLs as ``(media_type, url)`` tuples.

        Each connector module appends its own.

        :rtype: list
        """
        return []

    @api.depends("media_type", "remote_ref", "username")
    def _compute_account_url(self):
        for account in self:
            account.account_url = ""
            for val_url in account._fields_account_url():
                if len(val_url) < 2:
                    continue
                if account.media_type == val_url[0]:
                    account.account_url = val_url[1]
                    break

    def compute_dashboard_statistics(self):
        """Recompute the figures the dashboard shows, without asking anybody.

        What the client calls when the kanban loads. It is pure aggregation
        over rows that are already stored, so opening the dashboard costs no
        call at all and can happen as often as the user wants.

        :return: whether anything was recomputed.
        :rtype: bool
        """
        accounts = self or self.sudo().search([])
        return accounts._refresh_account_statistics()

    def refresh_dashboard_statistics(self):
        """Ask the social media for the figures again, from the dashboard.

        What the client calls when somebody presses *Update*. Unlike
        :meth:`compute_dashboard_statistics` this one does spend calls — one
        per account, against the endpoint that fills the daily series — and
        that is the point: the user is saying he does not want to wait for the
        two-hour cron. It is the same thing
        :meth:`action_refresh_statistics` already does from the account form,
        over every account instead of one.

        Refreshing the series first and aggregating afterwards is not
        optional: the figures come from those rows, so the other order would
        recompute the card from what was already on screen.

        There is no throttle. There was one while opening the dashboard cost
        calls; now it costs none, and throttling the button would make it look
        broken, which is exactly what the button is there to fix.

        :return: whether anything was refreshed.
        :rtype: bool
        """
        accounts = self or self.sudo().search([])
        refreshed = accounts._refresh_statistics()
        accounts._refresh_account_statistics()
        return refreshed

    def _refresh_account_statistics(self):
        """Recompute the figures of the account from what Odoo already stores.

        Not an empty hook, and it does not talk to the social media. The
        dashboard calls it on every load, so anything it asked for would be
        paid once per load and would grow with the history of the account;
        what it does instead is add up rows that are already here.

        Two sources, in this order: the daily series when the account has one,
        because those rows are the figures of the whole page and not only of
        what Odoo published, so it is both the cheaper answer and the truer
        one; and failing that the counters already stored on the publications,
        so a social media reporting nothing by day keeps whatever its last
        import left instead of dropping to zero.

        ``engagement`` is averaged, never added up. It is a ratio, and the
        daily series says so itself with ``group_operator="avg"``.

        Written with ``sudo()`` for the same reason the time series is: a
        regular user has to be able to refresh his own account.

        :return: whether anything was recomputed.
        :rtype: bool
        """
        counters = self._interaction_count_fields() + ["impression_count"]
        refreshed = False
        for account in self:
            values = account._account_statistics_from_series(counters)
            if values is None:
                values = account._account_statistics_from_posts(counters)
            if values is None:
                continue
            account.sudo().write(values)
            refreshed = True
        return refreshed

    def _account_statistics_from_series(self, counters):
        """Aggregate the daily series of this account, or ``None`` if it has none.

        ``None`` and an account whose figures are genuinely zero are different
        answers, and the caller needs to tell them apart to know whether to
        fall back. That is why this does not simply return zeros.

        :param list counters: counter fields to add up.
        :rtype: dict or None
        """
        self.ensure_one()
        statistics = self.env["social.account.statistics"].sudo()
        return self._aggregate_statistics(
            statistics, [("account_id", "=", self.id)], counters
        )

    def _account_statistics_from_posts(self, counters):
        """Add up the counters already stored on the publications.

        The fallback for a social media that reports nothing by day. It asks
        for nothing: whatever was last imported into the publications is what
        is added up, and with nothing importing them the figures stay at zero,
        which is the truth — base never learned them.

        :param list counters: counter fields to add up.
        :rtype: dict or None
        """
        self.ensure_one()
        post_accounts = self.env["social.post.account"].sudo()
        return self._aggregate_statistics(
            post_accounts, [("account_id", "=", self.id)], counters
        )

    def _aggregate_statistics(self, records, domain, counters):
        """Add up ``counters`` over ``domain``, averaging the engagement.

        Shared by the two sources so they cannot disagree on the one rule that
        matters, which is that a ratio is averaged and everything else is
        summed. A counter a connector added to
        :meth:`~._interaction_count_fields` may not exist on both models — the
        daily series is not built on ``social.statistics.mixin`` — so only the
        fields the model really has are asked for.

        :param records: the model to aggregate, already ``sudo()``.
        :param list domain: what to aggregate over.
        :param list counters: counter fields to add up.
        :return: the values to write, or ``None`` when nothing was found.
        :rtype: dict or None
        """
        fnames = [fname for fname in counters if fname in records._fields]
        aggregates = ["__count"] + [f"{fname}:sum" for fname in fnames]
        if "engagement" in records._fields:
            aggregates.append("engagement:avg")
        [values] = records._read_group(domain=domain, aggregates=aggregates)
        if not values[0]:
            return None
        result = {
            fname: value or 0 for fname, value in zip(fnames, values[1:], strict=False)
        }
        if "engagement" in records._fields:
            result["engagement"] = values[-1] or 0
        return result

    def _snapshot_statistics(self, date_from, date_to):
        """Write one ``social.account.statistics`` row per day of the range.

        Empty hook: a connector implements it only if its API reports figures
        per day. The ones that only publish lifetime counters leave it alone,
        and their accounts simply have no time series.

        :param date_from: first day to write, included.
        :param date_to: last day to write, included.
        """
        return

    def _refresh_statistics(self):
        """Write the time series again over the last days.

        Empty hook, the narrow one of the two that write the series: the
        social media revise the figures of days already past, so the last ones
        are asked for again instead of being trusted as final. How many days
        that is belongs to each connector, which is also what answering here
        means. Reading the history further back is not base's — it grows with
        the account and belongs to whoever synchronizes it.

        :return: whether a connector took care of these accounts.
        :rtype: bool
        """
        return False

    def _write_statistics_rows(self, statistics_by_date):
        """Create or update the rows of this account for the given days.

        This is the only place the time series is written, so the connectors
        do not each reinvent the upsert the ``unique (account_id, date)``
        constraint asks for.

        The rows are written with ``sudo()``. They mirror what the social
        media reported and belong to the owner of ``account_id``, so nothing
        is decided here; a regular user only reads them, and the *Update
        statistics* button of his own account has to work all the same.

        :param dict statistics_by_date: measures by ``date``, keyed by field
            name.
        :return: the rows written.
        :rtype: recordset
        """
        self.ensure_one()
        statistics_model = self.env["social.account.statistics"].sudo()
        statistics_by_day = {
            fields.Date.to_date(date): statistics
            for date, statistics in (statistics_by_date or {}).items()
        }
        if not statistics_by_day:
            return statistics_model.browse()
        existing = statistics_model.search(
            [("account_id", "=", self.id), ("date", "in", list(statistics_by_day))]
        )
        rows_by_day = {row.date: row for row in existing}
        to_create = []
        for day, statistics in statistics_by_day.items():
            row = rows_by_day.get(day)
            if row:
                row.write(statistics)
            else:
                to_create.append(dict(statistics, account_id=self.id, date=day))
        return existing + statistics_model.create(to_create)

    def validate_access_token(self):
        """Hook for the connector modules to refresh an expired token.

        Called before every operation on the social media, so connectors
        keep it cheap and answer from the stored expiry dates.
        """

    def action_validate_access_token(self):
        """Check the token against the social media, from the account form.

        The user asking whether the token works expects a real answer: the
        stored dates cannot tell a token that was revoked on the social media side.
        ``check_remote_token`` is what connectors use to tell this deliberate
        check from the guard that runs before every call.
        """
        self.ensure_one()
        return self.with_context(check_remote_token=True).validate_access_token()

    def _refresh_credentials(self):
        """Renew the credentials of this account without asking the user.

        Hook for the connector modules whose social media allows it. Called
        when a publication was refused because of the credentials, so it must
        answer whether the caller can try again.

        :return: whether the account can be used again.
        :rtype: bool
        """
        return False

    def _flag_credentials_expired(self, message):
        """Record that this account needs the user to authorize it again.

        The credentials cannot be renewed from Odoo anymore, and whoever
        notices is a cron or somebody publishing on another account: the flag
        is what puts the warning on the dashboard, and the note is what
        reaches the user in charge of the account.

        :param message: the reason the social media gave.
        """
        self.ensure_one()
        if not self.need_update:
            self.sudo().write({"need_update": True})
            self._need_update()
        self.message_post(
            body=_(
                "The credentials of the account are no longer valid and could "
                "not be renewed: %(error)s. Update the account to authorize "
                "it again.",
                error=message,
            ),
            partner_ids=self.user_id.partner_id.ids,
        )

    def _clear_credentials_flag(self):
        """Take down the warning the expired credentials put on the dashboard.

        The counterpart of :meth:`_flag_credentials_expired`, which is what its
        docstring already promised: a new authorization clears the flag and
        nothing else does. Until now nothing in base did, and the flag only
        ever went down as a side effect of the import, which is not base's any
        more.

        Called on a successful re-authorization, so it checks nothing: whoever
        calls it has just proven the credentials work.
        """
        flagged = self.filtered("need_update")
        if not flagged:
            return
        flagged.sudo().write({"need_update": False})
        flagged._need_update(need_update=False)

    def _get_check_media_updates_domain(self):
        """Return the accounts :meth:`~._run_check_media_updates` goes through.

        Every account, as far as base is concerned: renewing the credentials
        and writing the daily series are wanted on all of them. It is a hook
        because a module that also reads the social media may have a reason to
        leave an account out for a while, and that reason is never base's to
        know.

        :rtype: list
        """
        return []

    def _run_check_media_updates(self):
        """Check for new updates on the social media.

        Every run also renews the credentials that are about to expire, so a
        token does not run out between two publications: the connectors answer
        from their stored expiry dates, so an account whose token is still
        good costs nothing. Each account is checked in its own savepoint, and
        the one that cannot be renewed is flagged instead of dropping the run
        of the others.

        The cron record does not set a user, so the search needs ``sudo()`` to
        reach the accounts of every responsible, and the tokens themselves are
        restricted to the administrators.

        Only the credentials the social media refused, raised by the connectors
        as ``SocialCredentialsError``, flag the account: the flag is cleared by
        a new authorization and by nothing else, so a timeout or a bug in a
        connector must not ask the user to authorize an account again.

        Which accounts are checked is asked to
        :meth:`~._get_check_media_updates_domain`, so a module with a reason to
        leave some of them out says so there instead of here.

        :return: whether new updates were found.
        :rtype: bool
        """
        for account in self.sudo().search(self._get_check_media_updates_domain()):
            try:
                with self.env.cr.savepoint():
                    account.with_context(not_notify=True).validate_access_token()
            except psycopg2.OperationalError as error:
                if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                _logger.exception(
                    "Error checking the credentials of the account %s", account.id
                )
            except SocialCredentialsError as error:
                _logger.warning(
                    "The credentials of the account %(account)s are no longer "
                    "valid: %(error)s",
                    {"account": account.id, "error": error},
                )
                account._flag_credentials_expired(str(error))
            except Exception:  # noqa: BLE001 - one account must not stop the rest
                _logger.exception(
                    "Error checking the credentials of the account %s", account.id
                )
        return False

    def _need_update(self, need_update=True):
        """Flag pending updates on the dashboard of the responsible users.

        The check runs in a cron, whose user is not the one owning the
        account, so the message has to be addressed to each responsible user.

        The payload names the accounts because the dashboard has to tell the
        user which one to act on: somebody responsible for four accounts on
        three social media can do nothing with a notice that only says
        *something needs updating*. Each partner is told about his own
        accounts and about no others.
        """
        partners = self.user_id.partner_id or self.env.user.partner_id
        for partner in partners:
            accounts = self.filtered(
                lambda account, partner=partner: account.user_id.partner_id == partner
            )
            self.env["bus.bus"]._sendone(
                partner,
                "social_need_update",
                {
                    "need_update": need_update,
                    "accounts": [
                        {
                            "id": account.id,
                            "name": account.name,
                            "media": account.media_id.name,
                        }
                        for account in accounts
                    ],
                },
            )

    @api.model
    def _get_social_dashboard_url(self):
        """Return the URL of the Social Media dashboard.

        Used by the OAuth callbacks to land the user on the dashboard
        instead of the default app.
        """
        menu = self.env.ref(
            "social_media_base.social_dashboard_menu",
            raise_if_not_found=False,
        )
        if menu and menu.action:
            return f"/web#menu_id={menu.id}&action={menu.action.id}"
        return "/web"

    def _get_default_filter_date(self, start_date, end_date, months=1):
        """Complete the bounds of a statistics window that were left out.

        :param start_date: first moment asked for, ``months`` back when
            missing.
        :param end_date: last moment asked for, now when missing.
        :param months: how far back the default start reaches.
        :return: the ``(start, end)`` pair of the window.
        :rtype: tuple
        """
        start = start_date or (fields.Datetime.now() - relativedelta(months=months))
        end = end_date or fields.Datetime.now()
        return start, end
