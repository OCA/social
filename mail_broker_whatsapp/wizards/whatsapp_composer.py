# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsappComposer(models.TransientModel):

    _name = "whatsapp.composer"

    res_model = fields.Char("Document Model Name")
    res_id = fields.Integer("Document ID")
    number_field_name = fields.Char()
    find_broker = fields.Boolean()
    broker_id = fields.Many2one(
        "mail.broker", domain=[("broker_type", "=", "whatsapp")], required=True
    )
    body = fields.Text("Message")

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        brokers = self.env["mail.broker"].search([("broker_type", "=", "whatsapp")])
        result["find_broker"] = len(brokers) != 1
        if not result["find_broker"]:
            result["broker_id"] = brokers.id
        return result

    def _action_send_whatsapp(self):
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.broker_id)
        channel.message_post(
            body=self.body, subtype_xmlid="mail.mt_comment", message_type="comment"
        )

    def action_view_whatsapp(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.broker_id)
        if channel:
            return {
                "type": "ir.actions.client",
                "tag": "mail.action_discuss",
                "params": {"active_id": "{}_{}".format(channel._name, channel.id)},
            }
        return False

    def action_send_whatsapp(self):
        self.ensure_one()
        if not self.body:
            raise UserError(_("Body is required"))
        self._action_send_whatsapp()
        return False
