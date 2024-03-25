# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import Command, models


class MailBrokerAbstract(models.AbstractModel):
    _name = "mail.broker.abstract"

    def _verify_update(self, bot_data, kwargs):
        return True

    def _receive_update(self, broker, kwargs):
        pass

    def _update_content_after_hook(self, channel, message):
        pass

    def _set_webhook(self, broker):
        broker.integrated_webhook_state = "integrated"

    def _remove_webhook(self, broker):
        broker.integrated_webhook_state = False

    def _get_channel(self, broker, token, update, force_create=False):
        chat_id = broker._get_channel_id(token)
        if chat_id:
            return broker.env["mail.channel"].browse(chat_id)
        if not force_create and broker.has_new_channel_security:
            return False
        channel = broker.env["mail.channel"].create(
            self._get_channel_vals(broker, token, update)
        )
        channel._broadcast(channel.channel_member_ids.mapped("partner_id").ids)
        return channel

    def _get_author(self, broker, update):
        return False

    def _get_channel_vals(self, broker, token, update):
        author = self._get_author(broker, update)
        members = [
            Command.create({"partner_id": partner.id, "is_pinned": True})
            for partner in broker.member_ids.partner_id
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
            "token": token,
            "broker_id": broker.id,
            "channel_type": "broker",
            "channel_member_ids": members,
        }

    def _send(
        self, broker, record, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        raise NotImplementedError()
