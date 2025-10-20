# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class CrmLead(models.Model):
    """Feature #5: Extend CRM Lead to link with Facebook leads"""

    _inherit = "crm.lead"

    fb_lead_id = fields.Char(
        string="Facebook Lead ID",
        readonly=True,
        help="Facebook Lead ID if this lead was imported from Facebook Lead Ads",
        index=True,
    )
    social_lead_id = fields.Many2one(
        "social.lead",
        string="Facebook Lead",
        readonly=True,
        help="Link to the original Facebook lead data",
        ondelete="set null",
    )
