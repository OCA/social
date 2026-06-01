# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import fields, models


class MailChannel(models.Model):
    _inherit = "discuss.channel"

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

    # def _to_store(self, store: Store, fields):
    #     super()._to_store(store, fields)
    #     if not self:
    #         return
    #
    #     for record in self:
    #         gateway = record.gateway_id
    #         if not gateway:
    #             continue
    #
    #         store.add(
    #             record,
    #             {
    #                 "gateway": {
    #                     "id": gateway.id,
    #                     "name": gateway.name,
    #                     "type": gateway.gateway_type,
    #                 },
    #                 "gateway_name": gateway.name,
    #                 "gateway_id": gateway.id,
    #             },
    #         )

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

    def message_post(
        self, *, message_type="notification", gateway_type=False, **kwargs
    ):
        message = super().message_post(
            message_type=message_type,
            gateway_type=gateway_type or self.gateway_id.gateway_type,
            **kwargs,
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

    def _message_update_content(
        self,
        message,
        body,
        attachment_ids=None,
        partner_ids=None,
        strict=True,
        **kwargs,
    ):
        res = super()._message_update_content(
            message=message,
            body=body,
            attachment_ids=attachment_ids,
            partner_ids=partner_ids,
            strict=strict,
            **kwargs,
        )
        if self.channel_type == "gateway" and message.gateway_notification_ids:
            self.env[
                f"mail.gateway.{self.gateway_id.gateway_type}"
            ]._update_content_after_hook(self, message)
        return res
