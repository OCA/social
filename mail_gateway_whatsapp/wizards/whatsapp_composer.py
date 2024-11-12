# Copyright 2022 CreuBlanca
# Copyright 2024 Tecnativa - Carlos López
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WhatsappComposer(models.TransientModel):

    _name = "whatsapp.composer"
    _description = "Compose a whatsapp message"

    res_model = fields.Char("Document Model Name")
    res_id = fields.Integer("Document ID")
    number_field_name = fields.Char()
    find_gateway = fields.Boolean()
    gateway_id = fields.Many2one(
        "mail.gateway", domain=[("gateway_type", "=", "whatsapp")], required=True
    )
    template_id = fields.Many2one(
        "mail.whatsapp.template",
        domain="""[
            ('gateway_id', '=', gateway_id),
            ('state', '=', 'approved'),
            ('is_supported', '=', True)
        ]""",
    )
    body = fields.Text("Message")
    is_required_template = fields.Boolean(compute="_compute_is_required_template")

    @api.depends("res_model", "res_id", "number_field_name", "gateway_id")
    def _compute_is_required_template(self):
        MailMessage = self.env["mail.message"]
        for wizard in self:
            if (
                not wizard.res_model
                or not wizard.gateway_id
                or not wizard.number_field_name
            ):
                wizard.is_required_template = False
                continue
            record = self.env[wizard.res_model].browse(wizard.res_id)
            is_required_template = True
            channel = record._whatsapp_get_channel(
                wizard.number_field_name, wizard.gateway_id
            )
            if channel:
                last_message = MailMessage.search(
                    [
                        ("gateway_type", "=", "whatsapp"),
                        ("model", "=", channel._name),
                        ("res_id", "=", channel.id),
                    ],
                    order="date desc",
                    limit=1,
                )
                if last_message:
                    delta = (datetime.now() - last_message.date).total_seconds() / 3600
                    if delta < 24.0:
                        is_required_template = False
            wizard.is_required_template = is_required_template

    @api.onchange("gateway_id")
    def onchange_gateway_id(self):
        self.template_id = False

    @api.onchange("template_id")
    def onchange_template_id(self):
        if self.template_id:
            self.body = self.template_id.body

    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        gateways = self.env["mail.gateway"].search([("gateway_type", "=", "whatsapp")])
        result["find_gateway"] = len(gateways) != 1
        if not result["find_gateway"]:
            result["gateway_id"] = gateways.id
        return result

    def _action_send_whatsapp(self):
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)
        channel.with_context(whatsapp_template_id=self.template_id.id).message_post(
            body=self.body, subtype_xmlid="mail.mt_comment", message_type="comment"
        )

    def action_view_whatsapp(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record:
            return
        channel = record._whatsapp_get_channel(self.number_field_name, self.gateway_id)
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
