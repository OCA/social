# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json

from odoo import api, fields, models
from odoo.tools import file_open


class SocialAccount(models.Model):
    _name = "social.account"
    _inherit = ["avatar.mixin", "social.media.base.mixin"]
    _description = "Social Account"

    """
        This model defines the accounts associated with the different social medias.
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

    image_1920 = fields.Image(default=_default_image)

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
    enviroment = fields.Selection(
        [("test", "Test"), ("production", "Production")], default="test"
    )
    need_update = fields.Boolean(default=False)

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
            for post in post_ids:
                if len(post.account_ids) == 1:
                    post.write(
                        {
                            "active": False,
                        }
                    )
            account.write(
                {
                    "active": False,
                }
            )

    def _compute_display_name(self):
        for account in self:
            account.display_name = (
                f"[{account.media_type.upper()}] {account.name}"
                if account.media_type
                else account.name
            )

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
