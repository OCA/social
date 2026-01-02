# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import file_open

from ..social_utils import _generate_timestamps, get_weeks


class SocialAccount(models.Model):
    _name = "social.account"
    _inherit = ["avatar.mixin", "social.media.base.mixin"]
    _description = "Social Account"

    """
        This model defines the accounts associated with the different social networks.
    """

    name = fields.Char()
    active = fields.Boolean(default=True)
    username = fields.Char()
    media_id = fields.Many2one("social.media", ondelete="restrict")
    media_type = fields.Selection(related="media_id.media_type")
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    advertising_account_id = fields.Char()
    last_update_account = fields.Datetime()
    post_account_ids = fields.One2many("social.post.account", "account_id")

    @api.model
    def _default_image(self):
        return base64.b64encode(file_open("base/static/img/avatar.png", "rb").read())

    image_1920 = fields.Image(default=lambda self: self._default_image())
    # Use media platform icon for kanban group headers
    # Override avatar_128 to show platform logo instead of account image
    avatar_128 = fields.Image(
        compute="_compute_avatar_128",
        store=False,
        help="Platform logo dynamically retrieved from social.media.image",
    )
    avatar_256 = fields.Image(
        compute="_compute_avatar_256",
        store=False,
        help="Platform logo in 256x256 for better quality",
    )

    @api.depends("media_id", "media_id.image")
    def _compute_avatar_128(self):
        """Use platform logo as avatar for group headers"""
        for account in self:
            if account.media_id and account.media_id.image:
                # Dynamically get platform logo from social.media
                account.avatar_128 = account.media_id.image
            else:
                # Fallback to account image if no media linked
                account.avatar_128 = account.image_128

    @api.depends("media_id", "media_id.image")
    def _compute_avatar_256(self):
        """Use platform logo for higher resolution displays"""
        for account in self:
            if account.media_id and account.media_id.image:
                # Dynamically get platform logo from social.media
                account.avatar_256 = account.media_id.image
            else:
                # Fallback to account image
                account.avatar_256 = account.image_256

    # STATISTICS
    comment_count = fields.Integer(default=0)
    like_count = fields.Integer(default=0)
    click_count = fields.Integer(default=0)
    share_count = fields.Integer(default=0)
    interactions_count = fields.Integer(
        compute="_compute_interactions_count",
        store=True,
        default=0,
        help="""
            Indicates the interactions with the
            publication (clicks, likes, comments,shares).
        """,
    )
    impression_count = fields.Integer(
        default=0,
        help="""
            Total number of views, which may include
            multiple views by the same user.
        """,
    )
    engagement = fields.Float(default=0)

    account_url = fields.Char(compute="_compute_account_url", store=True)
    environment = fields.Selection(
        [("test", "Test"), ("production", "Production")], default="test"
    )
    need_update = fields.Boolean(default=False)
    show_post_calendar = fields.Boolean(
        default=False, help="Defines whether to display upcoming posts in the calendar."
    )

    # SECURITY
    access_token = fields.Char()
    refresh_access_token = fields.Char()
    expire_access_token_date = fields.Date()
    is_property_account = fields.Boolean(
        default=False, compute="_compute_is_property_account"
    )

    @api.depends_context("uid")
    def _compute_is_property_account(self):
        for account in self:
            account.is_property_account = self.env.user == account.create_uid

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

    def delete_account(self):
        """
        Archive social media account.

        This method is used to delete the social account,
        as well as all its associated posts and campaigns.
        It also marks all the associated posts and campaigns
        as inactive.
        """
        SocialPostAccount = self.env["social.post.account"]
        SocialPost = self.env["social.post"]
        UtmCampaign = self.env["utm.campaign"]
        for account in self:
            SocialPostAccount.search([("account_id", "=", account.id)]).write(
                {
                    "active": False,
                }
            )
            UtmCampaign.search([("account_id", "=", account.id)]).write(
                {
                    "active": False,
                }
            )
            post_ids = SocialPost.search([("account_ids", "in", account.id)])
            posts_to_archive = post_ids.filtered(lambda p: len(p.account_ids) == 1)
            posts_to_archive.write({"active": False})
            account.write(
                {
                    "active": False,
                }
            )

    def _compute_display_name(self):
        """Display clean account name - platform icon shown via avatar widget"""
        for account in self:
            # Show just the account name - the platform logo/icon will be displayed
            # via the many2one_avatar widget which uses avatar_128/avatar_256 fields
            # that are computed to show media_id.image dynamically
            account.display_name = account.name or "Unnamed Account"

    def _fields_account_url(self):
        return []

    @api.depends(lambda self: [val[0] for val in self._fields_account_url()])
    def _compute_account_url(self):
        for account in self:
            for val_url in account._fields_account_url():
                if len(val_url) < 2:
                    continue
                if account.media_id.media_type:
                    account.account_url = (
                        val_url[1] if account.media_id.media_type in val_url[0] else ""
                    )
                else:
                    continue

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
        """
        Returns a list of dictionaries containing statistics
        for the specified social media account, formatted correctly
        for display in the chart view.

        :param start_date: Start date and time of the period
        :param end_date: End date and time of the period
        :param granularity: Level of granularity for the statistics
                            (e.g., WEEK, MONTH, YEAR)
        :return: List of dictionaries
        :rtype: dict
        """
        return []

    def get_chart_account_statistics(
        self, start_date=None, end_date=None, granularity="WEEK"
    ):
        return self._get_chart_account_statistics(start_date, end_date, granularity)

    def _update_posts_statistics(self, post_id, domain):
        """
        Update posts and statistics.

        :param post_id: ID of the post
        :param domain: Domain of the post
        :return: List of dictionaries
        :rtype: list
        """
        return []

    def update_posts_statistics(self, post_id=None, domain=None):
        """
        Update posts and  statistics
        """
        statistics = self._update_posts_statistics(post_id, domain)
        return json.dumps(statistics)

    def validate_access_token(self):
        """
        Validates the access token for the social media account.
        """
        pass

    def _load_ads_accounts(self):
        """
        Returns a dictionary containing the ads accounts of the social media account.

        :return: Dictionary containing ads accounts
        :rtype: dict
        """
        return {}

    def load_ads_accounts(self):
        return self._load_ads_accounts()

    def _run_check_media_updates(self):
        """
        Checks for social media updates.
        This method is used to check for any new social media updates.

        :return: True if new updates are found, otherwise False
        :rtype: bool
        """
        return False

    def _need_update(self, need_update=True):
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "social_need_update",
            {"need_update": need_update},
        )

    def _get_default_filter_date(self, start_date, end_date, time_date=False, months=1):
        start = start_date or (datetime.now() - relativedelta(months=months))
        end = end_date or (datetime.now())
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
            )

            def map_chart_data(chart_statistics, label, key_data=0):
                dataset = {
                    "pointStyle": "circle",
                    "pointRadius": 10,
                    "pointHoverRadius": 15,
                    "label": self.env._(label),
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
                    "name": self.env._(
                        "[{media}] {name}",
                        media=self.media_type.upper(),
                        name=self.name,
                    ),
                    "impressionCount": impression_count,
                    "commentCount": comment_count,
                    "reactionCount": reaction_count,
                    "chartLabel": self.env._("Statistics"),
                    "labels": [week for week in chart_weeks],
                    "datasets": [
                        map_chart_data(statistics_values, "Clicks", 0),
                        map_chart_data(statistics_values, "Shares", 3),
                        map_chart_data(statistics_values, "Likes", 1),
                        map_chart_data(statistics_values, "Comments", 2),
                        map_chart_data(
                            statistics_values,
                            "Impressions",
                            5,
                        ),
                        map_chart_data(statistics_values, "Engagement", 4),
                    ],
                }
            )
        return data_chart
