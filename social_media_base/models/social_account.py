# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import logging

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import file_open

from ..social_utils import _generate_timestamps, get_weeks

_logger = logging.getLogger(__name__)


class SocialAccount(models.Model):
    """Account associated with a social media."""

    _name = "social.account"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "avatar.mixin",
        "social.media.base.mixin",
    ]
    _description = "Social Account"

    @api.model
    def _default_image(self):
        return base64.b64encode(file_open("base/static/img/avatar.png", "rb").read())

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
        help="Identifier of this account on the social network. It is set by "
        "the connector module of each social media.",
    )
    advertising_account_id = fields.Char()
    last_update_account = fields.Datetime()
    post_account_ids = fields.One2many("social.post.account", "account_id")
    image_1920 = fields.Image(default=lambda self: self._default_image())

    comment_count = fields.Integer(default=0)
    like_count = fields.Integer(default=0)
    click_count = fields.Integer(default=0)
    share_count = fields.Integer(default=0)
    interactions_count = fields.Integer(
        compute="_compute_interactions_count",
        store=True,
        default=0,
        help="Interactions with the publication: clicks, likes, comments and shares.",
    )
    impression_count = fields.Integer(
        default=0,
        help="Total number of views, which may include multiple views by the "
        "same user.",
    )
    engagement = fields.Float(default=0, digits=(16, 2))

    account_url = fields.Char(compute="_compute_account_url")
    enviroment = fields.Selection(
        [("test", "Test"), ("production", "Production")], default="test"
    )
    need_update = fields.Boolean(default=False)

    access_token = fields.Char(groups="base.group_system")
    refresh_access_token = fields.Char(groups="base.group_system")
    expire_access_token_date = fields.Date(string="Expire Access Token")
    is_property_account = fields.Boolean(
        default=False, compute="_compute_is_property_account"
    )
    can_manage_account = fields.Boolean(
        compute="_compute_can_manage_account",
        help="Whether the current user may update or archive this account: "
        "its responsible user and the social media administrators.",
    )

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_is_property_account(self):
        for account in self:
            account.is_property_account = self.env.user == account.user_id

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_can_manage_account(self):
        is_manager = self.env.user.has_group(
            "social_media_base.group_social_media_manager"
        )
        for account in self:
            account.can_manage_account = is_manager or account.user_id == self.env.user

    def update_account(self):
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

    def action_archive_account(self):
        """Archive the accounts and their whole footprint.

        Nothing is removed from the social network: relinking the account
        reactivates everything.
        """
        self.write(
            {
                "active": False,
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
                self.env._(
                    "The account %(account)s belongs to another company.",
                    account=account_sudo.display_name,
                )
            )
        if self.env.user.has_group("social_media_base.group_social_media_manager"):
            return
        if account_sudo.user_id != self.env.user:
            raise AccessError(
                self.env._(
                    "The account %(account)s is already associated with "
                    "another user. Ask its responsible user or a social "
                    "media administrator to relink it.",
                    account=account_sudo.display_name,
                )
            )

    def action_purge_account(self):
        """Delete the accounts and their publication history from Odoo only.

        Campaigns are kept: ``utm.campaign`` is shared with other
        applications and may be linked to leads, orders or mailings.

        :return: the accounts list action, the current record no longer exists.
        :rtype: dict
        """
        if not self.env.user.has_group("social_media_base.group_social_media_manager"):
            raise AccessError(
                self.env._("Only a social media administrator can delete an account.")
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
        accounts.unlink()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "social_media_base.social_account_action"
        )
        action["target"] = "main"
        return action

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

        Dashboard posts, campaigns, campaign groups and the posts whose only
        account is one of them.
        """
        SocialPostAccount = self.env["social.post.account"].with_context(
            active_test=False
        )
        SocialPost = self.env["social.post"].with_context(active_test=False)
        UtmCampaign = self.env["utm.campaign"].with_context(active_test=False)
        SocialPostAccount.search(
            [("account_id", "in", self.ids), ("active", "!=", active)]
        ).write({"active": active})
        campaigns = UtmCampaign.search(
            [("account_id", "in", self.ids), ("active", "!=", active)]
        )
        campaigns.write({"active": active})
        post_ids = SocialPost.search(
            [("account_ids", "in", self.ids), ("active", "!=", active)]
        )
        post_ids.filtered(lambda post: len(post.account_ids) == 1).write(
            {"active": active}
        )
        groups = campaigns.campaign_group_id
        if active:
            groups.filtered(lambda group: not group.active).write({"active": True})
        else:
            for group in groups.filtered("active"):
                has_active_campaign = (
                    self.env["utm.campaign"]
                    .with_context(active_test=True)
                    .search_count([("campaign_group_id", "=", group.id)], limit=1)
                )
                if not has_active_campaign:
                    group.write({"active": False})

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

    @api.depends("click_count", "like_count", "share_count", "comment_count")
    def _compute_interactions_count(self):
        for account in self:
            account.interactions_count = (
                account.click_count
                + account.like_count
                + account.share_count
                + account.comment_count
            )

    def _filter_statistics(self, entity_statistics):
        post_statistics = {
            "click_count": 0,
            "like_count": 0,
            "comment_count": 0,
            "share_count": 0,
            "engagement": 0,
            "impression_count": 0,
        }
        for __, statistics in entity_statistics.items():
            post_statistics["click_count"] += statistics[0]
            post_statistics["like_count"] += statistics[1]
            post_statistics["comment_count"] += statistics[2]
            post_statistics["share_count"] += statistics[3]
            post_statistics["engagement"] += statistics[4]
            post_statistics["impression_count"] += statistics[5]
        return post_statistics

    def _get_chart_account_statistics(self, start_date, end_date, granularity):
        """Return the account statistics formatted for the chart view.

        :param start_date: start of the period.
        :param end_date: end of the period.
        :param granularity: WEEK, MONTH or YEAR.
        :rtype: list
        """
        return []

    def get_chart_account_statistics(
        self, account_id=None, start_date=None, end_date=None, granularity="WEEK"
    ):
        account = self.browse(account_id) if account_id else self
        return account._get_chart_account_statistics(start_date, end_date, granularity)

    def _update_posts_statistics(self, post_id, domain):
        """Update the posts and their statistics.

        :param post_id: post to update, all of them when not set.
        :param domain: additional domain on the posts.
        :rtype: list
        """
        return []

    def update_posts_statistics(self, post_id=None, domain=None):
        statistics = self._update_posts_statistics(post_id, domain)
        return json.dumps(statistics)

    def validate_access_token(self):
        """Hook for the connector modules to refresh an expired token."""

    def action_import_campaigns(self):
        """Import the campaign groups and campaigns from the social network.

        :return: ``success``, ``message`` and the number of imported
            ``groups``, ``campaigns`` and ``ads``.
        :rtype: dict
        """
        self.ensure_one()
        return {
            "success": False,
            "message": self.env._(
                "Importing campaigns is not available for this social media."
            ),
            "groups": 0,
            "campaigns": 0,
            "ads": 0,
        }

    def action_import_campaigns_notify(self):
        """Import the campaigns and show the result as a notification."""
        res = self.action_import_campaigns()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if res.get("success") else "danger",
                "message": res.get("message"),
            },
        }

    def _load_ads_accounts(self):
        """Return the ads accounts of this social media account.

        ``ads`` is always a list so the client action always receives an
        iterable, whatever the connector modules add to it.

        :rtype: dict
        """
        return {"ads": []}

    def load_ads_accounts(self):
        return self._load_ads_accounts()

    def _run_check_media_updates(self):
        """Check for new updates on the social network.

        :return: whether new updates were found.
        :rtype: bool
        """
        return False

    def _trigger_initial_sync(self):
        """Run the posts-statistics sync now so the dashboard is populated
        right after linking an account."""
        cron = self.env.ref(
            "social_media_base.initial_sync_account_job", raise_if_not_found=False
        )
        if cron:
            cron.sudo()._trigger()

    def _need_update(self, need_update=True):
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "social_need_update",
            {"need_update": need_update},
        )

    @api.model
    def _get_social_dashboard_url(self):
        """Return the URL of the Social Media dashboard.

        Used by the OAuth callbacks to land the user on the dashboard
        instead of the default app.
        """
        menu = self.env.ref(
            "social_media_base.social_network_stream_post_menu",
            raise_if_not_found=False,
        )
        if menu and menu.action:
            return f"/web#menu_id={menu.id}&action={menu.action.id}"
        return "/web"

    def _get_default_filter_date(self, start_date, end_date, time_date=False, months=1):
        start = start_date or (fields.Datetime.now() - relativedelta(months=months))
        end = end_date or fields.Datetime.now()
        if time_date:
            return _generate_timestamps(date_start=start, date_end=end)
        return start, end

    def _map_chart_statistics(self, account_statistics, **values):
        data_chart = []
        statistics_values = (
            account_statistics.values()
            if isinstance(account_statistics, dict)
            else account_statistics
        )
        if statistics_values and self.media_type:
            chart_weeks = get_weeks(
                values.get(
                    "start_date",
                ),
                values.get(
                    "end_date",
                ),
                freq=values.get("freq", "W-MON"),
                env=self.env,
            )

            def map_chart_data(chart_statistics, label, key_data=0):
                dataset = {
                    "pointStyle": "circle",
                    "pointRadius": 10,
                    "pointHoverRadius": 15,
                    "label": label,
                    "data": [
                        statistics[key_data]
                        for statistics in chart_statistics
                        if len(statistics) > key_data
                    ],
                }
                return dataset

            impression_count = sum(
                [
                    statistics[5]
                    for statistics in statistics_values
                    if len(statistics) > 5
                ]
            )
            comment_count = sum(
                [
                    statistics[2]
                    for statistics in statistics_values
                    if len(statistics) > 2
                ]
            )
            reaction_count = sum(
                [
                    statistics[1] + statistics[3]
                    for statistics in statistics_values
                    if len(statistics) > 1 and len(statistics) > 3
                ]
            )
            data_chart.append(
                {
                    "id": self.id,
                    "name": f"[{self.media_type.upper()}] {self.name}",
                    "impressionCount": impression_count,
                    "commentCount": comment_count,
                    "reactionCount": reaction_count,
                    "chartLabel": self.env._("Statistics"),
                    "labels": [week for week in chart_weeks],
                    "datasets": [
                        map_chart_data(statistics_values, self.env._("Clicks"), 0),
                        map_chart_data(statistics_values, self.env._("Shares"), 3),
                        map_chart_data(statistics_values, self.env._("Likes"), 1),
                        map_chart_data(statistics_values, self.env._("Comments"), 2),
                        map_chart_data(
                            statistics_values,
                            self.env._("Impressions"),
                            5,
                        ),
                        map_chart_data(statistics_values, self.env._("Engagement"), 4),
                    ],
                }
            )
        return data_chart
