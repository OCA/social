# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import psycopg2

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from ..social_advertising_utils import ADVERTISING_ENVIRONMENTS

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """Advertising side of a social media account."""

    _inherit = "social.account"

    environment = fields.Selection(
        ADVERTISING_ENVIRONMENTS,
        default="test",
        required=True,
        help="Which entities the advertising APIs answer for this account. In "
        "Test the social media only returns the test advertising accounts, "
        "their campaigns and their ads, which are never served nor billed. "
        "This setting does not affect the publication of posts.",
    )
    advertising_account_ids = fields.One2many(
        "social.advertising.account",
        "account_id",
        string="Advertising Accounts",
    )
    advertising_account_urn = fields.Char(
        string="Advertising Account Reference",
        compute="_compute_advertising_account_urn",
        store=True,
        help="Remote reference of the advertising account in use, the value "
        "the connector modules send to the social media.",
    )
    can_sync_advertising_accounts = fields.Boolean(
        compute="_compute_can_sync_advertising_accounts",
        help="Technical field: whether a connector module can list the "
        "advertising accounts of this social media.",
    )
    campaign_count = fields.Integer(compute="_compute_campaign_counts")
    campaign_group_count = fields.Integer(compute="_compute_campaign_counts")
    ad_ids = fields.One2many("social.advertising.ad", "account_id", string="Ads")
    ad_count = fields.Integer(compute="_compute_ad_count")
    ads_need_update = fields.Boolean(
        readonly=True,
        copy=False,
        help="Technical field: the social media has ads this account does "
        "not know about yet. It is raised by the cron checking for new ads "
        "and cleared by the next synchronization.",
    )

    @api.depends(
        "advertising_account_ids.campaign_ids",
        "advertising_account_ids.campaign_group_ids",
    )
    def _compute_campaign_counts(self):
        """Count the campaigns and the groups of every advertising account.

        The counts cover all the advertising accounts of the social media
        account, not only the one in use: the entities of the others were
        imported too and stay reachable.
        """
        advertising_accounts = self.advertising_account_ids
        campaigns = dict(
            self.env["social.advertising.campaign"]._read_group(
                domain=[("advertising_account_id", "in", advertising_accounts.ids)],
                groupby=["advertising_account_id"],
                aggregates=["__count"],
            )
        )
        groups = dict(
            self.env["social.advertising.campaign.group"]._read_group(
                domain=[("advertising_account_id", "in", advertising_accounts.ids)],
                groupby=["advertising_account_id"],
                aggregates=["__count"],
            )
        )
        for account in self:
            account.campaign_count = sum(
                campaigns.get(advertising_account, 0)
                for advertising_account in account.advertising_account_ids
            )
            account.campaign_group_count = sum(
                groups.get(advertising_account, 0)
                for advertising_account in account.advertising_account_ids
            )

    @api.depends("ad_ids")
    def _compute_ad_count(self):
        counts = dict(
            self.env["social.advertising.ad"]._read_group(
                domain=[("account_id", "in", self.ids)],
                groupby=["account_id"],
                aggregates=["__count"],
            )
        )
        for account in self:
            account.ad_count = counts.get(account, 0)

    def _purge_linked_records(self):
        """Delete the campaigns and groups these accounts brought along.

        A campaign or a group that exists on the social media is a mirror of
        it, and the account is the only way to reach it: without one it can
        neither be synchronized nor published again, so it goes with the
        account. What was created in Odoo and never reached the social media
        is never deleted, it only loses the accounts being purged: it is
        work of the user, not a mirror.

        A campaign shared with an account that stays is kept as well, and
        loses only the accounts going away.
        """
        res = super()._purge_linked_records()
        advertising_accounts = self.advertising_account_ids
        campaigns = (
            self.env["social.advertising.campaign"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("account_ids", "in", self.ids),
                    ("advertising_account_id", "in", advertising_accounts.ids),
                ]
            )
        )
        remote_campaigns = campaigns.filtered(
            lambda campaign: campaign.remote_ref and not (campaign.account_ids - self)
        )
        groups = (
            self.env["social.advertising.campaign.group"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("remote_ref", "!=", False),
                    ("advertising_account_id", "in", advertising_accounts.ids),
                ]
            )
        )
        kept = campaigns - remote_campaigns
        if kept:
            kept.write(
                {"account_ids": [Command.unlink(account.id) for account in self]}
            )
        remote_campaigns.unlink()
        # A group is only dropped once it holds nothing: a campaign of
        # another account, or one written by hand, keeps its group alive.
        groups.filtered(lambda group: not group.campaign_ids).unlink()
        return res

    def action_open_ads(self):
        """Open the ads of this account."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "social_media_advertising.social_advertising_ad_action"
        )
        action["domain"] = [("account_id", "=", self.id)]
        action["context"] = {"default_account_id": self.id}
        return action

    def action_open_campaigns(self):
        """Open the campaigns of the advertising accounts of this account."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Campaigns"),
            "res_model": "social.advertising.campaign",
            "view_mode": "tree,form",
            "domain": [
                ("advertising_account_id", "in", self.advertising_account_ids.ids)
            ],
            "context": {"default_account_ids": [Command.set(self.ids)]},
        }

    def action_open_campaign_groups(self):
        """Open the campaign groups of the advertising accounts of this account."""
        self.ensure_one()
        current = self.advertising_account_ids.filtered("is_current")[:1]
        return {
            "type": "ir.actions.act_window",
            "name": _("Campaign Groups"),
            "res_model": "social.advertising.campaign.group",
            "view_mode": "tree,form",
            "domain": [
                ("advertising_account_id", "in", self.advertising_account_ids.ids)
            ],
            "context": {"default_advertising_account_id": current.id}
            if current
            else {},
        }

    @api.depends(
        "advertising_account_ids.is_current",
        "advertising_account_ids.remote_ref",
    )
    def _compute_advertising_account_urn(self):
        for account in self:
            current = account.advertising_account_ids.filtered("is_current")[:1]
            account.advertising_account_urn = current.remote_ref or False

    @api.depends("media_id.media_type")
    def _compute_can_sync_advertising_accounts(self):
        media_types = self._advertising_media_types()
        for account in self:
            account.can_sync_advertising_accounts = account.media_type in media_types

    def write(self, vals):
        """Drop the advertising account in use when the environment changes.

        The two environments never share an advertising account, so the one
        that was in use cannot belong to the new one. The new environment may
        leave a single candidate, which is then chosen right away.
        """
        accounts = self.browse()
        if "environment" in vals:
            accounts = self.filtered(
                lambda account: account.environment != vals["environment"]
            )
        res = super().write(vals)
        accounts.advertising_account_ids.sudo().write({"is_current": False})
        for account in accounts:
            account._autoselect_advertising_account()
        return res

    @api.model
    def _advertising_media_types(self):
        """Return the media types able to list their advertising accounts.

        Each connector module appends its own, which is what makes the
        advertising settings of the account form show up.

        :rtype: list
        """
        return []

    def _fetch_advertising_accounts(self):
        """Return the advertising accounts of this account, as value dicts.

        Each connector module fetches them from its social media and maps
        them to the fields of ``social.advertising.account``. ``remote_ref``
        is mandatory and is what identifies an advertising account.

        :rtype: list
        """
        self.ensure_one()
        return []

    def _sync_advertising_accounts(self):
        """Refresh the advertising accounts stored for this account.

        The records mirror the social media, so they are created, updated and
        dropped from what :meth:`_fetch_advertising_accounts` answers. They
        are written with ``sudo()``: a regular user reads them but never
        writes them, and the refresh is triggered from his own account.

        The choice of the user is left alone: refreshing the list must not
        change which advertising account is in use, it only picks one when
        none was chosen yet and the environment leaves a single candidate,
        see :meth:`_autoselect_advertising_account`. Nothing is dropped when
        the social media answers nothing at all either, because an empty
        answer cannot be told apart from a transient failure, and dropping
        the one in use would leave every campaign endpoint without its scope.

        :return: The advertising accounts of this account after the refresh.
        :rtype: recordset
        """
        self.ensure_one()
        AdvertisingAccount = self.env["social.advertising.account"].sudo()
        values_by_ref = {
            values["remote_ref"]: values
            for values in self._fetch_advertising_accounts()
            if values.get("remote_ref")
        }
        existing = AdvertisingAccount.search([("account_id", "=", self.id)])
        if not values_by_ref:
            return existing
        now = fields.Datetime.now()
        stale = AdvertisingAccount
        for advertising_account in existing:
            values = values_by_ref.pop(advertising_account.remote_ref, None)
            if values:
                advertising_account.write(dict(values, last_sync_date=now))
            else:
                stale |= advertising_account
        stale.unlink()
        if values_by_ref:
            AdvertisingAccount.create(
                [
                    dict(values, account_id=self.id, last_sync_date=now)
                    for values in values_by_ref.values()
                ]
            )
        self.invalidate_recordset(["advertising_account_ids"])
        self._autoselect_advertising_account()
        return AdvertisingAccount.search([("account_id", "=", self.id)])

    def _autoselect_advertising_account(self):
        """Choose the advertising account when there is nothing to choose.

        A single advertising account in the environment of the social media
        account is the one every campaign endpoint would be scoped to
        anyway, so asking the user to pick it adds nothing. An advertising
        account already in use is never replaced.

        :return: The advertising account chosen here, empty when the user
            still has to choose one.
        :rtype: recordset
        """
        self.ensure_one()
        AdvertisingAccount = self.env["social.advertising.account"]
        if self.advertising_account_ids.filtered("is_current"):
            return AdvertisingAccount
        candidates = self.advertising_account_ids.filtered(
            lambda advertising_account: advertising_account.environment
            == self.environment
        )
        if len(candidates) != 1:
            return AdvertisingAccount
        candidates._set_current()
        return candidates

    def _get_advertising_account(self, remote_ref):
        """Return the advertising account of this account for a reference.

        :param remote_ref: Reference of the advertising account on the
            social media.
        :rtype: recordset
        """
        self.ensure_one()
        return (
            self.env["social.advertising.account"]
            .sudo()
            .search(
                [("account_id", "=", self.id), ("remote_ref", "=", remote_ref)],
                limit=1,
            )
        )

    def action_sync_advertising_accounts(self):
        """Fetch the advertising accounts from the social media.

        :return: ``success``, ``message`` and the number of ``accounts``.
        :rtype: dict
        """
        self.ensure_one()
        if not self.can_sync_advertising_accounts:
            return {
                "success": False,
                "message": _(
                    "Listing the advertising accounts is not available for "
                    "this social media."
                ),
                "accounts": 0,
            }
        try:
            advertising_accounts = self._sync_advertising_accounts()
        except UserError as error:
            return {"success": False, "message": str(error), "accounts": 0}
        return {
            "success": True,
            "message": _(
                "%(accounts)s advertising account(s) available.",
                accounts=len(advertising_accounts),
            ),
            "accounts": len(advertising_accounts),
        }

    def action_sync_advertising_accounts_notify(self):
        """Fetch the advertising accounts and show the result as a notification.

        The notification chains a soft reload so the list of advertising
        accounts shows what was just fetched without the user reloading the
        view by hand.
        """
        res = self.action_sync_advertising_accounts()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if res.get("success") else "danger",
                "message": res.get("message"),
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _fetch_ads(self):
        """Return the ads of this account, as the social media answers them.

        Each connector module returns the values of its own ads, ready to be
        written on ``social.advertising.ad``. Every entry must carry a
        ``remote_ref``: it is what tells an ad already known apart from a new
        one.

        :rtype: list
        """
        self.ensure_one()
        return []

    def _sync_ads(self):
        """Mirror the ads of the social media into this database.

        The records mirror the social media, so they are created and updated
        from what :meth:`_fetch_ads` answers. They are written with
        ``sudo()``: a regular user reads them but never writes them, and the
        refresh is triggered from his own account.

        An ad that is not answered anymore is archived, never deleted: its
        statistics are the only trace left of what it did. Nothing is
        archived when the social media answers nothing at all either,
        because an empty answer cannot be told apart from a transient
        failure.

        The connectors only answer for the advertising account in use, so
        the ads that are missing from the answer are only looked for among
        the advertising accounts it covered. Otherwise choosing another
        advertising account would archive everything fetched from the
        previous one.

        :return: The ads of this account after the refresh.
        :rtype: recordset
        """
        self.ensure_one()
        Ad = self.env["social.advertising.ad"].sudo()
        values_by_ref = {
            values["remote_ref"]: values
            for values in self._fetch_ads()
            if values.get("remote_ref")
        }
        existing = Ad.with_context(active_test=False).search(
            [("account_id", "=", self.id)]
        )
        if not values_by_ref:
            return existing
        now = fields.Datetime.now()
        fetched_scope = {
            values.get("advertising_account_id") or False
            for values in values_by_ref.values()
        }
        stale = Ad
        for ad in existing:
            values = values_by_ref.pop(ad.remote_ref, None)
            if values:
                ad.write(dict(values, active=True, last_sync_date=now))
            elif (ad.advertising_account_id.id or False) in fetched_scope:
                stale |= ad
        stale.filtered("active")._register_remote_ad_gone()
        if values_by_ref:
            Ad.create(
                [
                    dict(values, account_id=self.id, last_sync_date=now)
                    for values in values_by_ref.values()
                ]
            )
        if self.ads_need_update:
            self.sudo().write({"ads_need_update": False})
        self.invalidate_recordset(["ad_ids"])
        return Ad.search([("account_id", "=", self.id)])

    def action_sync_ads(self):
        """Fetch the ads from the social media.

        :return: ``success``, ``message`` and the number of ``ads``.
        :rtype: dict
        """
        self.ensure_one()
        if not self.can_sync_advertising_accounts:
            return {
                "success": False,
                "message": _("Listing the ads is not available for this social media."),
                "ads": 0,
            }
        try:
            ads = self._sync_ads()
        except UserError as error:
            return {"success": False, "message": str(error), "ads": 0}
        return {
            "success": True,
            "message": _("%(ads)s ad(s) available.", ads=len(ads)),
            "ads": len(ads),
        }

    @api.model
    def _get_advertising_accounts_domain(self):
        """Return the domain of the accounts a connector serves ads for.

        The media types are filtered in the domain instead of reading
        ``can_sync_advertising_accounts`` on every account: an account of a
        social media whose connector module is not installed must not even
        be read.

        :rtype: list
        """
        return [("media_id.media_type", "in", self._advertising_media_types())]

    @api.model
    def action_sync_all_ads_notify(self):
        """Fetch the ads of every account the user can see, from the ads view.

        Each account is synchronized in its own savepoint: the ads the
        social media already answered for an account must survive the
        failure of the next one. Errors are summed up in the notification
        instead of interrupting the run, because the user is looking at the
        ads of every account at once.
        """
        accounts = self.search(self._get_advertising_accounts_domain())
        ads = 0
        failures = []
        for account in accounts:
            try:
                with self.env.cr.savepoint():
                    res = account.action_sync_ads()
            except psycopg2.OperationalError as error:
                if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                _logger.exception("Error syncing the ads of the account %s", account.id)
                failures.append(account.display_name)
                continue
            except Exception:  # noqa: BLE001 - one account must not stop the rest
                _logger.exception("Error syncing the ads of the account %s", account.id)
                failures.append(account.display_name)
                continue
            if res.get("success"):
                ads += res.get("ads", 0)
            else:
                failures.append(account.display_name)
        if not accounts:
            message = _("No account of yours can serve ads.")
        elif failures:
            message = _(
                "%(ads)s ad(s) available. The ads of these accounts could not "
                "be fetched: %(accounts)s.",
                ads=ads,
                accounts=", ".join(failures),
            )
        else:
            message = _("%(ads)s ad(s) available.", ads=ads)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "danger" if failures else "success",
                "message": message,
            },
        }

    def _fetch_ad_refs(self):
        """Return the references of the ads the social media serves.

        This is the cheap half of :meth:`_fetch_ads`: connector modules only
        list the ads, without asking for their statistics, their campaigns
        nor the posts they promote. It is what the cron checks with, so
        looking for news costs a single call.

        :rtype: set
        """
        self.ensure_one()
        return set()

    def _check_ads_updates(self):
        """Raise the flag when the social media serves ads not known here.

        Only new ads are reported. An ad that disappeared is not news the
        user has to act on: the next synchronization archives it anyway.

        :return: whether new ads were found.
        :rtype: bool
        """
        self.ensure_one()
        remote_refs = self._fetch_ad_refs()
        if not remote_refs:
            return False
        known = set(
            self.env["social.advertising.ad"]
            .sudo()
            .with_context(active_test=False)
            .search([("account_id", "=", self.id)])
            .mapped("remote_ref")
        )
        if remote_refs <= known:
            return False
        if not self.ads_need_update:
            self.sudo().write({"ads_need_update": True})
        self._notify_ads_need_update()
        return True

    @api.model
    def get_ads_need_update(self):
        """Return whether the accounts of the user have ads to synchronize.

        The kanban of the ads raises its badge from the bus, but a reload
        starts from scratch, so the flag stored by the cron has to be read
        back when the view is mounted. The record rules already restrict the
        search to the accounts the user is responsible for.

        :rtype: bool
        """
        return bool(self.search_count([("ads_need_update", "=", True)], limit=1))

    def _notify_ads_need_update(self, need_update=True):
        """Tell the responsible user that the social media has new ads.

        The check runs in a cron, whose user is not the one owning the
        account, so the message has to be addressed to each responsible
        user. The ads themselves are not fetched: the user decides when to
        synchronize.
        """
        partners = self.user_id.partner_id or self.env.user.partner_id
        for partner in partners:
            self.env["bus.bus"]._sendone(
                partner,
                "social_ads_need_update",
                {"need_update": need_update},
            )

    @api.model
    def _run_check_ads_updates(self):
        """Look for ads the social media serves and this database ignores.

        The cron record does not set a user, so the search needs ``sudo()``
        to reach the accounts of every responsible. Each account is checked
        in its own savepoint: the one whose social media is unreachable must
        not drop the check of the others.
        """
        for account in self.sudo().search(self._get_advertising_accounts_domain()):
            try:
                with self.env.cr.savepoint():
                    account._check_ads_updates()
            except psycopg2.OperationalError as error:
                if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                _logger.exception(
                    "Error checking the ads of the account %s", account.id
                )
            except Exception:  # noqa: BLE001 - one account must not stop the rest
                _logger.exception(
                    "Error checking the ads of the account %s", account.id
                )

    def action_import_campaigns(self):
        """Import the campaign groups and campaigns from the social media.

        :return: ``success``, ``message`` and the number of imported
            ``groups``, ``campaigns`` and ``ads``.
        :rtype: dict
        """
        self.ensure_one()
        return {
            "success": False,
            "message": _("Importing campaigns is not available for this social media."),
            "groups": 0,
            "campaigns": 0,
            "ads": 0,
        }

    def action_import_campaigns_notify(self):
        """Import the campaigns and show the result as a notification.

        The notification chains a soft reload so the campaign counters of the
        account show what was just imported without the user reloading the
        view by hand.
        """
        res = self.action_import_campaigns()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if res.get("success") else "danger",
                "message": res.get("message"),
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _propagate_active_to_related(self, active):
        """Archive or unarchive the campaigns and campaign groups too.

        A campaign may be shared by several accounts, so it is only archived
        once none of them is active anymore, the same rule the base module
        applies to the posts. The state of the accounts is what decides, not
        the ones being archived right now: archiving them one by one has to
        end up archiving the campaign as well.

        A campaign group follows the same rule, and it is also taken from the
        advertising accounts: a group that holds no campaign belongs to its
        account all the same and has to leave with it.

        The ads belong to a single account, so they simply follow it out.
        They are not brought back when the account is: an ad is also
        archived when it stops being served, and unarchiving them all would
        resurrect the ones the social media dropped. The next
        synchronization restores the ones still served.
        """
        res = super()._propagate_active_to_related(active)
        if not active:
            self.env["social.advertising.ad"].sudo().search(
                [("account_id", "in", self.ids)]
            ).write({"active": False})
        SocialAdvertisingCampaign = self.env[
            "social.advertising.campaign"
        ].with_context(active_test=False)
        campaigns = SocialAdvertisingCampaign.search(
            [("account_ids", "in", self.ids), ("active", "!=", active)]
        )
        if not active:
            campaigns = campaigns.filtered(
                lambda campaign: not campaign.account_ids.filtered("active")
            )
        campaigns.write({"active": active})
        # A campaign group holding no campaign at all is not reachable through
        # them, so the groups of the advertising accounts are added: otherwise
        # an empty group would survive the archiving of its own account.
        groups = (
            campaigns.campaign_group_id
            | self.with_context(
                active_test=False
            ).advertising_account_ids.campaign_group_ids
        )
        if active:
            groups.filtered(lambda group: not group.active).write({"active": True})
        else:
            candidates = groups.filtered("active")
            if candidates:
                # Which groups still hold an active campaign is read in a
                # single query instead of one per group.
                group_ids_with_campaign = {
                    group.id
                    for (group,) in self.env["social.advertising.campaign"]
                    .with_context(active_test=True)
                    ._read_group(
                        [("campaign_group_id", "in", candidates.ids)],
                        ["campaign_group_id"],
                    )
                }
                candidates.filtered(
                    lambda group: group.id not in group_ids_with_campaign
                ).write({"active": False})
        return res
