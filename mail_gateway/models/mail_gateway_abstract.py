# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, models


class MailGatewayAbstract(models.AbstractModel):
    _name = "mail.gateway.abstract"
    _description = "Gateway abstract for functions"

    def _verify_update(self, bot_data, kwargs):
        return True

    def _receive_update(self, gateway, kwargs):
        pass

    def _post_process_message(self, message, channel):
        self.env["mail.notification"].search(
            [("gateway_channel_id", "=", channel.id), ("is_read", "=", False)]
        )._set_read_gateway()

    def _post_process_reply(self, related_message):
        pass

    def _update_content_after_hook(self, channel, message):
        pass

    def _set_webhook(self, gateway):
        gateway.integrated_webhook_state = "integrated"

    def _remove_webhook(self, gateway):
        gateway.integrated_webhook_state = False

    def _get_channel(self, gateway, token, update, force_create=False):
        chat_id = gateway._get_channel_id(token)
        if chat_id:
            return gateway.env["discuss.channel"].browse(chat_id)
        if not force_create and gateway.has_new_channel_security:
            return False
        channel = gateway.env["discuss.channel"].create(
            self._get_channel_vals(gateway, token, update)
        )
        channel._broadcast(channel.channel_member_ids.mapped("partner_id").ids)
        return channel

    def _get_author(self, gateway, update):
        return False

    def _get_channel_vals(self, gateway, token, update):
        author = self._get_author(gateway, update)
        members = [
            Command.create({"partner_id": partner.id, "unpin_dt": False})
            for partner in gateway.member_ids.partner_id
        ]
        if author:
            members.append(
                Command.create(
                    {
                        "partner_id": author._name == "res.partner" and author.id,
                        "guest_id": author._name == "mail.guest" and author.id,
                    }
                )
            )
        return {
            "gateway_channel_token": token,
            "gateway_id": gateway.id,
            "channel_type": "gateway",
            "channel_member_ids": members,
            "company_id": gateway.company_id.id,
        }

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        raise NotImplementedError()

    def _get_message_body(self, record):
        return record.mail_message_id.body
