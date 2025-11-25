# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class UtmCampaign(models.Model):
    _inherit = "utm.campaign"

    campaign_group_id = fields.Many2one("utm.group.campaign", string="Campaign group")
    allow_media_ids = fields.Many2many(
        "social.media", string="Media", compute="_compute_media_id"
    )
    media_id = fields.Many2one(
        "social.media", string="Allow Media", domain="[('id','in',allow_media_ids)]"
    )
    account_id = fields.Many2one(
        "social.account", string="Account", domain="[('media_id','in',allow_media_ids)]"
    )

    @api.depends("media_id", "account_id")
    def _compute_media_id(self):
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
        """
        Returns a list of available campaign media types.

        It is used to filter the available media types
        for a campaign.

        :return: A list of available campaign media types.
        :rtype: list
        """
        return []
