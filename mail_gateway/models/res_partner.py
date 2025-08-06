# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    """Update of res.partner class to take into account the gateway."""

    _inherit = "res.partner"

    gateway_channel_ids = fields.One2many(
        "res.partner.gateway.channel", inverse_name="partner_id"
    )

    def _get_channels_as_member(self):
        channels = super()._get_channels_as_member()
        if self.env.user.has_group("mail_gateway.gateway_user"):
            channels |= self.env["discuss.channel"].search(
                [
                    ("channel_type", "=", "gateway"),
                    (
                        "channel_member_ids",
                        "in",
                        self.env["discuss.channel.member"]
                        .sudo()
                        ._search(
                            [
                                ("partner_id", "=", self.id),
                                ("is_pinned", "=", True),
                            ]
                        ),
                    ),
                ]
            )
        return channels


class ResPartnerGatewayChannel(models.Model):
    _name = "res.partner.gateway.channel"
    _description = "Technical data used to get the gateway author"

    name = fields.Char(related="gateway_id.name")
    partner_id = fields.Many2one(
        "res.partner", required=True, readonly=True, ondelete="cascade"
    )
    gateway_id = fields.Many2one(
        "mail.gateway", required=True, readonly=True, ondelete="cascade"
    )
    gateway_token = fields.Char(readonly=True)
    company_id = fields.Many2one(
        "res.company", related="gateway_id.company_id", store=True
    )

    @api.depends_context("mail_gateway_partner_info")
    def _compute_display_name(self):
        # Be able to tell to which partner belongs the gateway partner channel
        # e.g.: picking it from a selector
        if not self.env.context.get("mail_gateway_partner_info"):
            return super()._compute_display_name()
        for gateway_channel in self:
            gateway_channel.display_name = (
                f"{gateway_channel.partner_id.display_name} ({gateway_channel.name})"
            )

    _sql_constraints = [
        (
            "unique_partner_gateway",
            "UNIQUE(partner_id, gateway_id)",
            "Partner can only have one configuration for each gateway.",
        ),
    ]

    def mail_format(self):
        return [r._mail_format() for r in self]

    def _mail_format(self):
        return {
            "id": self.id,
            "name": self.name,
            "gateway": {
                "id": self.gateway_id.id,
                "name": self.gateway_id.name,
                "type": self.gateway_id.gateway_type,
            },
        }
