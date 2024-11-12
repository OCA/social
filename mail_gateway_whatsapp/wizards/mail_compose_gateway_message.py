# Copyright 2024 Tecnativa - Carlos López
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import markupsafe

from odoo import api, fields, models


class MailComposeGatewayMessage(models.TransientModel):
    _inherit = "mail.compose.gateway.message"

    whatsapp_template_id = fields.Many2one(
        "mail.whatsapp.template",
        domain="""[
            ('state', '=', 'approved'),
            ('is_supported', '=', True)
        ]""",
    )

    @api.onchange("whatsapp_template_id")
    def onchange_whatsapp_template_id(self):
        if self.whatsapp_template_id:
            self.body = markupsafe.Markup(self.whatsapp_template_id.body)

    def _action_send_mail(self, auto_commit=False):
        if self.whatsapp_template_id:
            self = self.with_context(whatsapp_template_id=self.whatsapp_template_id.id)
        return super(MailComposeGatewayMessage, self)._action_send_mail(
            auto_commit=auto_commit
        )
