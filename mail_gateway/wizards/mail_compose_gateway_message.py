# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailComposeGatewayMessage(models.TransientModel):
    _name = "mail.compose.gateway.message"
    _inherit = "mail.compose.message"
    _description = "Mail Compose Gateway Message"

    wizard_partner_ids = fields.Many2many(
        "res.partner",
        "mail_compose_gateway_message_res_partner_rel",
        "wizard_id",
        "partner_id",
    )
    wizard_channel_ids = fields.Many2many(
        "res.partner.gateway.channel",
        "mail_compose_gateway_message_gateway_channel_rel",
        "wizard_id",
        "channel_id",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "mail_compose_gateway_message_ir_attachments_rel",
        "wizard_id",
        "attachment_id",
        "Attachments",
    )

    partner_ids = fields.Many2many(
        "res.partner",
        "mail_compose_gateway_message_res_partner_rel",
        "wizard_id",
        "partner_id",
        "Additional Contacts",
        domain=lambda r: r._partner_ids_domain(),
    )

    def get_mail_values(self, res_ids):
        self.ensure_one()
        res = super(MailComposeGatewayMessage, self).get_mail_values(res_ids)
        res[res_ids[0]]["gateway_notifications"] = [
            {
                "partner_id": channel.partner_id.id,
                "channel_type": "gateway",
                "gateway_channel_id": channel.id,
            }
            for channel in self.wizard_channel_ids
        ]
        return res
