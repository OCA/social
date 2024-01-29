# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_thread_by_email(self, message, recipients_data, **kwargs):
        partners_data = [r for r in recipients_data if r["notif"] == "gateway"]
        if partners_data:
            self._notify_thread_by_gateway(message, partners_data, **kwargs)
        return super()._notify_thread_by_email(message, recipients_data, **kwargs)

    def _notify_thread_by_gateway(self, message, partners_data, **kwargs):
        for partner_data in partners_data:
            if partner_data["notif"] != "gateway" or not partner_data.get(
                "gateway_channel_id"
            ):
                continue
            message._send_to_gateway_thread(
                self.env["res.partner.gateway.channel"].browse(
                    partner_data.get("gateway_channel_id")
                )
            )

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        if "gateway_notifications" in kwargs:
            result = []
            for notification in kwargs["gateway_notifications"]:
                if not notification.get("channel_type"):
                    continue
                partner = self.env["res.partner"].browse(notification["partner_id"])
                user = partner.user_ids
                follower_data = {
                    "active": partner.active,
                    "id": partner.id,
                    "is_follower": True,
                    "lang": partner.lang,
                    "groups": set(user.groups_id.ids),
                    "notif": notification.get("channel_type"),
                    "share": partner.partner_share,
                    "uid": user[:1].id,
                    "ushare": user and any(user.mapped("share")),
                    "gateway_channel_id": notification.get("gateway_channel_id"),
                }
                if follower_data["ushare"]:  # any type of share user
                    follower_data["type"] = "portal"
                elif follower_data[
                    "share"
                ]:  # no user, is share -> customer (partner only)
                    follower_data["type"] = "customer"
                else:  # has a user not share -> internal user
                    follower_data["type"] = "user"
                result.append(follower_data)
            return result
        return super()._notify_get_recipients(message, msg_vals, **kwargs)

    def _check_can_update_message_content(self, messages):
        # We can delete the messages comming from a gateway on not channels
        if self._name != "mail.channel":
            new_messages = messages.filtered(lambda r: not r.gateway_message_ids)
        else:
            new_messages = messages
        return super()._check_can_update_message_content(new_messages)

    def _message_update_content(
        self, message, body, attachment_ids=None, strict=True, **kwargs
    ):
        result = super()._message_update_content(
            message, body, attachment_ids=attachment_ids, strict=strict, **kwargs
        )
        if body == "":
            # Unlink the message
            for gateway_message in message.gateway_message_ids:
                gateway_message.gateway_message_id = False
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id,
                    "mail.message/insert",
                    {
                        "id": gateway_message.id,
                        "gateway_thread_data": gateway_message.sudo().gateway_thread_data,
                    },
                )
        return result
