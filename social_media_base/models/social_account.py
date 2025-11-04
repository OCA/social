# Copyright 2025 Kencove (https://www.kencove.com/)
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

    image_1920 = fields.Image(default=_default_image)
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

    def _get_chart_account_statistics(self, start_date, end_date, granularity):
        return []

    def get_chart_account_statistics(
        self, start_date=None, end_date=None, granularity="WEEK"
    ):
        return self._get_chart_account_statistics(start_date, end_date, granularity)

    def _update_posts_statistics(self, post_id, domain):
        return []

    def update_posts_statistics(self, post_id=None, domain=None):
        """
        Update posts and  statistics
        """
        statistics = self._update_posts_statistics(post_id, domain)
        return json.dumps(statistics)

    def validate_access_token(self):
        pass

    def _load_ads_accounts(self):
        return {}

    def load_ads_accounts(self):
        return self._load_ads_accounts()

    def _run_check_media_updates(self):
        return False
