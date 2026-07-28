# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class UtmCampaign(models.Model):
    _name = "utm.campaign"
    _inherit = ["utm.campaign", "mail.thread", "mail.activity.mixin"]

    name = fields.Char(tracking=True)
    title = fields.Char(tracking=True)
    campaign_group_id = fields.Many2one(
        "utm.group.campaign", string="Campaign group", tracking=True
    )
    allow_media_ids = fields.Many2many(
        "social.media", string="Allowed Media", compute="_compute_allow_media_ids"
    )
    media_id = fields.Many2one(
        "social.media", string="Media", domain="[('id','in',allow_media_ids)]"
    )
    account_id = fields.Many2one(
        "social.account", string="Account", domain="[('media_id','in',allow_media_ids)]"
    )
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this campaign on the social network. It is set by "
        "the connector module of each social media.",
    )

    @api.depends("media_id", "account_id")
    def _compute_allow_media_ids(self):
        SocialMedia = self.env["social.media"]
        for campaign in self:
            campaign.allow_media_ids = [
                Command.set(
                    SocialMedia.search(
                        [("media_type", "in", campaign._available_campaign())]
                    ).ids
                )
            ]

    def _available_campaign(self):
        """Return the media types allowed on a campaign.

        Connector modules append their own.

        :rtype: list
        """
        return []
