# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import api, fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    gateway_channel_token = fields.Char()
    anonymous_name = fields.Char()  # Same field we will use on im_livechat
    gateway_id = fields.Many2one("mail.gateway")
    gateway_message_ids = fields.One2many(
        "mail.notification",
        inverse_name="gateway_channel_id",
    )
    company_id = fields.Many2one("res.company", default=False)
    channel_type = fields.Selection(
        selection_add=[("gateway", "Gateway")], ondelete={"gateway": "set default"}
    )
    gateway_token = fields.Char(
        related="gateway_id.token",
        string="Gateway related Token",
        required=False,
    )

    def channel_info(self):
        result = super().channel_info()
        for record, item in zip(self, result):
            item["gateway"] = {
                "id": record.gateway_id.id,
                "name": record.gateway_id.name,
                "type": record.gateway_id.gateway_type,
            }
            item["gateway_name"] = record.gateway_id.name
            item["gateway_id"] = record.gateway_id.id
        return result

    def _generate_avatar_gateway(self):
        # We will use this function to set a default avatar on each module
        return False

    def _generate_avatar(self):
        if self.channel_type not in ("gateway"):
            return super()._generate_avatar()
        avatar = self._generate_avatar_gateway()
        if not avatar:
            return False
        return base64.b64encode(avatar.encode())

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *args, gateway_type=False, **kwargs):
        message = super().message_post(
            *args, gateway_type=gateway_type or self.gateway_id.gateway_type, **kwargs
        )
        if (
            self.gateway_id
            and not self.env.context.get("no_gateway_notification", False)
            and message.message_type != "notification"
        ):
            self.env["mail.notification"].create(
                {
                    "mail_message_id": message.id,
                    "gateway_channel_id": self.id,
                    "notification_type": "gateway",
                    "gateway_type": self.gateway_id.gateway_type,
                }
            ).send_gateway()
        return message

    def _message_update_content_after_hook(self, message):
        self.ensure_one()
        if self.channel_type == "gateway" and message.gateway_notification_ids:
            self.env[
                "mail.gateway.{}".format(self.gateway_id.gateway_type)
            ]._update_content_after_hook(self, message)
        return super()._message_update_content_after_hook(message=message)
