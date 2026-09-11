# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import timedelta

import psycopg2

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY
from odoo.tools import file_open

from ..exceptions import SocialCredentialsError

_logger = logging.getLogger(__name__)

# How far back the periodic refresh reads the figures of the publications.
# It is what keeps the cost of that pass fixed: the calls it spends depend on
# the days of the window and not on how much the account has published.
STATISTICS_WINDOW_DAYS = 30


class SocialAccount(models.Model):
    """Account associated with a social media."""

    _name = "social.account"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "avatar.mixin",
        "social.media.base.mixin",
        "social.statistics.mixin",
        "social.web.url.mixin",
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

    engagement = fields.Float(
        default=0,
        digits=(16, 4),
        compute="_compute_engagement",
        store=True,
        help="Interactions of the account over its impressions, as a ratio.",
    )

    need_update = fields.Boolean(
        default=False,
        help="The credentials of the account expired and it has to be "
        "authorized again. It means that and nothing else; an account with "
        "publications left to import is marked with posts_need_import, in "
        "the synchronization module.",
    )
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

    @api.depends("interactions_count", "impression_count")
    def _compute_engagement(self):
        """Rate of interactions over impressions, as a ratio.

        The default for a social media that does not report a rate of its own,
        and it is the definition LinkedIn documents for its ``engagement``.
        What counts as an interaction is not decided here: it comes from
        :meth:`~._interaction_count_fields`, which X widens with retweets and
        quotes.

        A connector whose social media reports its own rate overrides this
        compute and answers what it stored; it must not call the social media
        from here, because the dashboard recomputes on every load.
        """
        for account in self:
            account.engagement = (
                account.interactions_count / account.impression_count
                if account.impression_count
                else 0
            )

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
        """Count the marketing campaigns of the posts of every account.

        The two sides of :meth:`~._get_utm_campaigns` read as an aggregate
        for the whole recordset, so the dashboard costs two queries instead
        of two per account.
        """
        campaigns_by_account = defaultdict(set)
        for account, campaign in self.env["social.post.account"]._read_group(
            domain=[("account_id", "in", self.ids), ("campaign_id", "!=", False)],
            groupby=["account_id", "campaign_id"],
        ):
            campaigns_by_account[account].add(campaign.id)
        for accounts, campaign in self.env["social.post"]._read_group(
            domain=[("account_ids", "in", self.ids), ("campaign_id", "!=", False)],
            groupby=["account_ids", "campaign_id"],
        ):
            campaigns_by_account[accounts].add(campaign.id)
        for account in self:
            account.utm_campaign_count = len(campaigns_by_account[account])

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

        The figures of the recent publications are read back in the same
        press, over the same window the daily cron reads: one set to explain
        and one ceiling of cost, wherever the user presses. The notification
        keeps speaking of the daily series, which is the only part of this a
        social media can be unable to answer.
        """
        self.ensure_one()
        # ``media`` is what the notification is built around: without it
        # ``_format_user_notification`` answers an empty message and nothing
        # reaches the user at all. It already prefixes the social media, so
        # the name goes in raw: ``display_name`` would repeat it.
        media = self.media_type or self.media_id.name
        refreshed_series = self._refresh_statistics()
        self._refresh_window_statistics()
        if refreshed_series:
            self._notify_user_client(
                notif_type="social_form_success",
                notif_message=_("The statistics of the account were updated."),
                media=media,
                account_name=self.name,
            )
        else:
            self._notify_user_client(
                notif_type="social_form_info",
                notif_message=_(
                    "This social media does not report statistics by day, so "
                    "there is no history to update."
                ),
                media=media,
                account_name=self.name,
            )

    def _check_unique_credentials(self, domain, message):
        """Refuse credentials another account already holds.

        Archived accounts are checked too, as they keep their credentials,
        and the accounts of ``self`` are excluded, so updating the keys of an
        account is not rejected by its own. Called on the empty recordset
        nothing is excluded, which is the association flow.

        :param domain: the leaves identifying the credentials.
        :param message: what the user is told when they are taken.
        """
        accounts = self.sudo()
        taken = accounts.with_context(active_test=False).search_count(
            [("id", "not in", accounts.ids)] + domain,
            limit=1,
        )
        if taken:
            raise UserError(message)

    def _associate_account(
        self, media_type, remote_ref, values, username=None, create_values=None
    ):
        """Link an account of a social media, creating it when it is new.

        What every OAuth callback does with what its social media answered:
        the account already linked is updated and reactivated, and one that
        was never linked is created for the current user. Whether the linked
        account may be taken over is decided by
        :meth:`~._check_can_associate`, which raises when it may not.

        It does not call :meth:`~._on_account_associated`: a connector
        answering several accounts announces them once, when it has them all.

        :param media_type: the social media the account belongs to.
        :param remote_ref: identifier of the account on the social media.
        :param values: what the social media answered about the account.
        :param username: name of the account, for the accounts linked before
            ``remote_ref`` was stored.
        :param create_values: values written only when the account is new.
        :rtype: recordset of ``social.account``
        """
        account = self._find_account_to_associate(
            media_type, remote_ref, username=username
        )
        if not account:
            return self.sudo().create(
                dict(values, **(create_values or {}), user_id=self.env.user.id)
            )
        account._check_can_associate()
        if not account.active:
            values = dict(values, active=True)
        account.sudo().write(values)
        return account

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
        """Do what an account needs right after being linked.

        Base refreshes the figures of the account, which every connector
        answers with a fixed number of calls, so a freshly linked account has
        its card filled from the first moment even when nothing synchronizes
        it. Importing what the account already published is somebody else's
        business: ``social_media_sync`` extends this method to queue that
        import, whose cost grows with the history of the page.

        The daily series is filled right after, as far back as the social
        media reports it. It costs the connector a fixed number of calls too,
        so the card is drawn over the whole period from the first moment
        instead of growing a few days at a time.
        """
        self._refresh_statistics()
        self._backfill_statistics()
        self._refresh_account_statistics()

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
        """Return the domain of the accounts an uninstalled module touches.

        Its own method so a connector can narrow it or widen it without
        rewriting :meth:`~._remove_social_media`.

        :rtype: list
        """
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

        Nothing is removed from the social media: relinking the account
        reactivates everything. The scheduled posts whose date passed while
        the account was archived are sent back to draft instead of being
        published on the spot, which ``social.post.write`` does for every way
        of reactivating a post, see
        :meth:`~odoo.addons.social_media_base.models.social_post.SocialPost.
        _reset_overdue_schedule`.
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
        """Return the account URL of each media type, keyed by media type.

        Each connector module adds its own.

        :rtype: dict
        """
        return {}

    @api.depends("media_type", "remote_ref", "username")
    def _compute_web_url(self):
        """Only declares what the address of an account is built from."""
        return super()._compute_web_url()

    def _get_web_url(self):
        self.ensure_one()
        return self._fields_account_url().get(self.media_type, "")

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

        The figures of the recent publications are read back too, over the
        same window the daily cron reads: the button asks for the same set the
        cron does, so there is a single ceiling of cost and a single thing to
        explain.

        Refreshing what the social media reports first and aggregating
        afterwards is not optional: the figures of the card come from those
        rows and from the publications, so the other order would recompute it
        from what was already on screen.

        There is no throttle. Opening the dashboard costs no call at all, so
        the only calls there are to spare are the ones the user asked for by
        pressing the button, and a button that answers with the same figures
        looks broken — which is exactly what it is there to fix.

        :return: whether anything was refreshed.
        :rtype: bool
        """
        accounts = self or self.sudo().search([])
        refreshed = accounts._refresh_statistics()
        accounts._refresh_window_statistics()
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

        The connectors write rows and base derives the account: a row is a
        publication or a day, and nobody else writes these figures. The rate
        is not among them — it is derived from the counters this leaves
        behind, so it stays the rate of the account and not the mean of the
        rates of its rows.

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
        for nothing: whatever the last refresh left on the publications is what
        is added up. That refresh only reaches the recent ones, so the total of
        such an account is the total of its window and not of its history,
        which is as far as an account with no daily series can be known from
        here.

        :param list counters: counter fields to add up.
        :rtype: dict or None
        """
        self.ensure_one()
        post_accounts = self.env["social.post.account"].sudo()
        return self._aggregate_statistics(
            post_accounts, [("account_id", "=", self.id)], counters
        )

    def _aggregate_statistics(self, records, domain, counters):
        """Add up ``counters`` over ``domain``.

        Counters only: the engagement of the account is derived from the
        totals this returns, so aggregating the rate of each row would be
        answering the same question twice and with the wrong weights. A
        counter a connector added to :meth:`~._interaction_count_fields` may
        not exist on both models — the daily series is not built on
        ``social.statistics.mixin`` — so only the fields the model really has
        are asked for.

        :param records: the model to aggregate, already ``sudo()``.
        :param list domain: what to aggregate over.
        :param list counters: counter fields to add up.
        :return: the values to write, or ``None`` when nothing was found.
        :rtype: dict or None
        """
        fnames = [fname for fname in counters if fname in records._fields]
        aggregates = ["__count"] + [f"{fname}:sum" for fname in fnames]
        [values] = records._read_group(domain=domain, aggregates=aggregates)
        if not values[0]:
            return None
        return {
            fname: value or 0 for fname, value in zip(fnames, values[1:], strict=False)
        }

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

    def _backfill_statistics(self, force=False):
        """Write the time series as far back as the social media answers.

        Empty hook, the wide one of the two that write the series, and it
        lives here for the same reason ``_refresh_statistics`` does: what it
        costs does not grow with the account. A connector answers the whole
        period with a fixed number of calls -- the range asked for is what
        decides them, never the history of the page -- so base can ask for it
        the moment an account is linked, without anything synchronizing it.
        What does grow with the account is the import of the publications, and
        that one stays in ``social_media_sync``.

        How far back the period reaches is not decided here either: it is the
        API of each social media that decides how much of it it reports by day.

        :param force: ask for the period again even if it was already read.
            The connectors that can tell one case from the other skip an
            account whose series is already there, and this is what the
            *Rebuild statistics history* button passes to ask for it anyway.
        :rtype: None
        """
        return

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
        rows_by_day = existing.grouped("date")
        to_create = []
        for day, statistics in statistics_by_day.items():
            row = rows_by_day.get(day)
            if row:
                row.write(statistics)
            else:
                to_create.append(dict(statistics, account_id=self.id, date=day))
        return existing + statistics_model.create(to_create)

    def _statistics_window_domain(self):
        """Return the publications whose figures the periodic refresh reads.

        Only the ones that are online and were published inside the window: a
        line marked as deleted has nothing left to ask about, and one outside
        the window keeps the last figures that were read for it.

        The window is what keeps this pass affordable in
        ``social_media_base``: what it spends depends on the days it looks
        back and not on how much the account has published.

        :rtype: list
        """
        limit = fields.Datetime.now() - timedelta(days=STATISTICS_WINDOW_DAYS)
        return [
            ("account_id", "in", self.ids),
            ("state", "=", "posted"),
            ("remote_ref", "!=", False),
            ("published_date", ">=", limit),
        ]

    def _refresh_post_statistics(self, post_accounts):
        """Read the figures of these publications back from the social media.

        Empty hook, and the only place these figures are read: whichever pass
        wants them — the daily refresh of base, the *Update* button, the
        import of ``social_media_sync`` — hands its own lines here instead of
        asking the social media itself.

        The lines arrive already chosen: whoever calls decides which ones are
        worth a call, and this only spends it. Every connector takes the ones
        of its own media type and leaves the rest to the next, which is also
        what makes the answer meaningful — a line the social media did not
        report is not a line whose figures are zero.

        The connector stamps ``statistics_date`` on the lines it answers for,
        in the same write as the figures.

        :param post_accounts: the lines to read, every one of them with a
            ``remote_ref``.
        :return: the lines the social media really answered for.
        :rtype: recordset
        """
        return self.env["social.post.account"]

    def _refresh_window_statistics(self):
        """Read back the figures of the recent publications of these accounts.

        Each account goes inside its own savepoint
        (:meth:`~._account_guard`): the pass writes as it goes, so an account
        the social media refuses must neither undo what the previous ones
        already wrote nor stop the ones still to come.

        The lines are searched with ``sudo()`` for the same reason the daily
        series is written with it: they belong to the responsible of the
        account and nothing is decided here, so a regular user refreshing his
        own account has to reach them all the same.

        :return: the lines the social media answered for.
        :rtype: recordset
        """
        post_accounts = self.env["social.post.account"]
        refreshed = post_accounts
        for account in self:
            lines = post_accounts.sudo().search(account._statistics_window_domain())
            if not lines:
                continue
            with account._account_guard(
                "Error refreshing the statistics of the publications of "
                "the account %s"
            ):
                refreshed |= account._refresh_post_statistics(lines)
        return refreshed

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

        The counterpart of :meth:`_flag_credentials_expired`, and what its
        docstring promises: a new authorization clears the flag and nothing
        else does. Base lowers it nowhere else — not on a call that answered,
        not on an import that went through — because both of those happen just
        as well with credentials the social media is about to refuse.

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

    @api.model
    def _is_concurrency_error(self, error):
        """Whether the error is the one PostgreSQL raises on a lost race.

        :param error: the exception to look at.
        :rtype: bool
        """
        return (
            isinstance(error, psycopg2.OperationalError)
            and error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY
        )

    @contextmanager
    def _account_guard(self, log_message=None, on_error=None):
        """Isolate what is done on one account in its own savepoint.

        Every pass that walks the accounts writes as it goes, so a failure on
        one of them must neither undo what the previous ones wrote nor stop
        the ones still to come. The account that fails is rolled back on its
        own and the pass carries on with the next.

        The concurrency error of PostgreSQL is raised again on purpose, so the
        retry mechanism of Odoo still sees it.

        :param log_message: the message to log, with a single ``%s`` for the
            id of the account. Unused when ``on_error`` is given.
        :param on_error: called with the exception instead of logging, for the
            caller that answers a failure with something more than a log line.
        """
        self.ensure_one()
        try:
            with self.env.cr.savepoint():
                yield
        except Exception as error:  # noqa: BLE001 - one account cannot stop the rest
            if self._is_concurrency_error(error):
                raise
            if on_error is None:
                _logger.exception(log_message, self.id)
            else:
                on_error(error)

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

    @api.model
    def _run_refresh_post_statistics(self):
        """Read back the figures of the publications of the last days.

        The daily pass of the cron, and the reason the figures of a
        publication move at all without a synchronization module installed.
        What it spends is bounded by the window and not by the history of the
        account, which is what lets it live here.

        The cron record sets no user, so the search needs ``sudo()`` to reach
        the accounts of every responsible.

        Which accounts are walked is asked to
        :meth:`~._get_check_media_updates_domain`, the same one that already
        decides which accounts are worth reading, plus the ones whose
        credentials are still valid: an account waiting for a new
        authorization can only answer a refusal, so asking it spends a call to
        learn what the flag already says.

        :return: the lines the social media answered for.
        :rtype: recordset
        """
        domain = self._get_check_media_updates_domain() + [("need_update", "=", False)]
        return self.sudo().search(domain)._refresh_window_statistics()

    def _notify_accounts_by_partner(
        self, bus_type, need_update=True, payload_accounts=True
    ):
        """Raise or lower a notice on the dashboard of the responsible users.

        The checks that raise these notices run in crons, whose user is not
        the one owning the account, so the message has to be addressed to each
        responsible user. The fallback to the user of the environment is what
        covers the account with no responsible: grouping by the partner alone
        would file them all under an empty key.

        Each notice keeps its own bus type, and that is what tells them apart
        on the card: neither state implies the other and several can be drawn
        at once.

        :param bus_type: the type the client listens on for this notice.
        :param need_update: whether the notice goes up or comes down.
        :param payload_accounts: whether the payload names the accounts. The
            dashboard needs them to tell the user which one to act on:
            somebody responsible for four accounts can do nothing with a
            notice that only says *something needs updating*. Each partner is
            told about his own accounts and about no others.
        """
        partners = self.user_id.partner_id or self.env.user.partner_id
        for partner in partners:
            payload = {"need_update": need_update}
            if payload_accounts:
                accounts = self.filtered(
                    lambda account, partner=partner: (
                        account.user_id.partner_id == partner
                    )
                )
                payload["accounts"] = [
                    {
                        "id": account.id,
                        "name": account.name,
                        "media": account.media_id.name,
                    }
                    for account in accounts
                ]
            self.env["bus.bus"]._sendone(partner, bus_type, payload)

    def _need_update(self, need_update=True):
        """Flag pending updates on the dashboard of the responsible users."""
        self._notify_accounts_by_partner("social_need_update", need_update)

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
