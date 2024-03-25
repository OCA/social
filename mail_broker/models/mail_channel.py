# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import api, fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    token = fields.Char()
    anonymous_name = fields.Char()  # Same field we will use on im_livechat
    broker_id = fields.Many2one("mail.broker")
    broker_message_ids = fields.One2many(
        "mail.notification",
        inverse_name="broker_channel_id",
    )
    channel_type = fields.Selection(
        selection_add=[("broker", "Broker")], ondelete={"broker": "set default"}
    )
    broker_token = fields.Char(related="broker_id.token", store=True, required=False)

    def channel_info(self):
        result = super().channel_info()
        for record, item in zip(self, result):
            item["broker_name"] = record.broker_id.name
            item["broker_id"] = record.broker_id.id
        return result

    def _generate_avatar_broker(self):
        # We will use this function to set a default avatar on each module
        return False

    def _generate_avatar(self):
        if self.channel_type not in ("broker"):
            return super()._generate_avatar()
        avatar = self._generate_avatar_broker()
        if not avatar:
            return False
        return base64.b64encode(avatar.encode())

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *args, broker_type=False, **kwargs):
        message = super().message_post(
            *args, broker_type=broker_type or self.broker_id.broker_type, **kwargs
        )
        if (
            self.broker_id
            and not self.env.context.get("no_broker_notification", False)
            and message.message_type != "notification"
        ):
            self.env["mail.notification"].create(
                {
                    "mail_message_id": message.id,
                    "broker_channel_id": self.id,
                    "notification_type": "broker",
                    "broker_type": self.broker_id.broker_type,
                }
            ).send_broker()
        return message

    def _message_update_content_after_hook(self, message):
        self.ensure_one()
        if self.channel_type == "broker" and message.broker_notification_ids:
            self.env[
                "mail.broker.{}".format(self.broker_id.broker_type)
            ]._update_content_after_hook(self, message)
        return super()._message_update_content_after_hook(message=message)
