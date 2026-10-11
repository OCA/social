# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UtmGroupCampaign(models.Model):
    _inherit = "utm.group.campaign"

    linkedin_urn = fields.Char()
    currency_id = fields.Many2one("res.currency")
    campaign_ids = fields.One2many("utm.campaign", "campaign_group_id")
    total_budget = fields.Float(
        help="""
        Maximum budget that the campaign can spend over its entire duration
    """
    )
