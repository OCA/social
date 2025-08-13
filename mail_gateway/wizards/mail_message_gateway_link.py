# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessageGatewayLink(models.TransientModel):
    _name = "mail.message.gateway.link"
    _description = "Link message from gateway"

    message_id = fields.Many2one("mail.message")
    resource_ref = fields.Reference(
        string="Record reference", selection="_selection_target_model"
    )

    @api.model
    def _selection_target_model(self):
        models = self.env["ir.model"].search([("is_mail_thread", "=", True)])
        return [(model.model, model.name) for model in models]

    def link_message(self):
        new_message = self.resource_ref.message_post(
            body=self.message_id.body,
            author_id=self.message_id.author_id.id,
            gateway_type=self.message_id.gateway_type,
            date=self.message_id.date,
            # message_id=update.message.message_id,
            subtype_xmlid="mail.mt_comment",
            message_type="comment",
            attachment_ids=self.message_id.attachment_ids.ids,
            gateway_notifications=[],  # Avoid sending notifications
        )
        self.message_id.gateway_message_id = new_message
        self.message_id._bus_send_store(
            self.message_id,
            {
                "gateway_thread_data": self.message_id.sudo().gateway_thread_data,
            },
        )
