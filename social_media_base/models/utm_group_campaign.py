# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class UtmGroupCampaign(models.Model):
    _name = "utm.group.campaign"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "UTM Group Campaign"

    name = fields.Char()
    active = fields.Boolean(default=True)
    campaign_ids = fields.One2many("utm.campaign", "campaign_group_id")
    campaign_count = fields.Integer(compute="_compute_campaign_count")
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this campaign group on the social network. It is "
        "set by the connector module of each social media.",
    )

    @api.depends("campaign_ids")
    def _compute_campaign_count(self):
        counts = dict(
            self.env["utm.campaign"]._read_group(
                [("campaign_group_id", "in", self.ids)],
                ["campaign_group_id"],
                ["__count"],
            )
        )
        for group in self:
            group.campaign_count = counts.get(group, 0)

    def action_view_campaigns(self):
        """Open the campaigns linked to this campaign group."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Campaigns"),
            "res_model": "utm.campaign",
            "view_mode": "list,form",
            "domain": [("campaign_group_id", "=", self.id)],
            "context": {
                "default_campaign_group_id": self.id,
                "from_social_media": True,
            },
        }
