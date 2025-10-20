# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models
from odoo.tests import RecordCapturer


class MailMessage(models.Model):
    _inherit = "mail.message"

    gateway_type = fields.Selection(
        selection=lambda r: r.env["mail.gateway"]._fields["gateway_type"].selection
    )
    gateway_notification_ids = fields.One2many(
        "mail.notification",
        inverse_name="mail_message_id",
        domain=[("notification_type", "=", "gateway")],
    )
    gateway_channel_ids = fields.Many2many(
        "res.partner.gateway.channel", compute="_compute_gateway_channel_ids"
    )
    gateway_channel_data = fields.Json(compute="_compute_gateway_channel_ids")
    gateway_message_ids = fields.One2many(
        "mail.message",
        inverse_name="gateway_message_id",
        string="Child gateway messages",
    )
    gateway_message_id = fields.Many2one(
        "mail.message", string="Original gateway message"
    )
    gateway_thread_data = fields.Json(compute="_compute_gateway_thread_data")

    @api.depends("gateway_message_id")
    def _compute_gateway_thread_data(self):
        for record in self:
            gateway_thread_data = {}
            if record.gateway_message_id:
                gateway_thread_data.update(
                    {
                        "name": record.gateway_message_id.record_name,
                        "id": record.gateway_message_id.res_id,
                        "model": record.gateway_message_id.model,
                    }
                )
            record.gateway_thread_data = gateway_thread_data

    @api.depends("notification_ids", "gateway_message_ids")
    def _compute_gateway_channel_ids(self):
        for record in self:
            if self.env.user.has_group("mail_gateway.gateway_user"):
                partners = record.notification_ids.res_partner_id
                channels = partners.gateway_channel_ids.filtered(
                    lambda r, messages=record.gateway_message_ids: (
                        r.gateway_token,
                        r.gateway_id.id,
                    )
                    not in [
                        (
                            notification.gateway_channel_id.gateway_channel_token,
                            notification.gateway_channel_id.gateway_id.id,
                        )
                        for notification in messages.gateway_notification_ids
                    ]
                )
            else:
                channels = self.env["res.partner.gateway.channel"]
            record.gateway_channel_ids = channels
            record.gateway_channel_data = {
                "channels": channels.ids,
                "partners": channels.partner_id.ids,
            }

    @api.depends("gateway_notification_ids")
    def _compute_gateway_channel_id(self):
        for rec in self:
            if rec.gateway_notification_ids:
                rec.gateway_channel_id = rec.gateway_notification_ids[
                    0
                ].gateway_channel_id

    def _get_message_format_fields(self):
        result = super()._get_message_format_fields()
        result += ["gateway_type", "gateway_channel_data", "gateway_thread_data"]
        return result

    def _send_to_gateway_thread(self, gateway_channel_id):
        chat_id = gateway_channel_id.gateway_id._get_channel_id(
            gateway_channel_id.gateway_token
        )
        channel = self.env["discuss.channel"].browse(chat_id)
        with RecordCapturer(
            self.env["mail.notification"], [("gateway_channel_id", "=", channel.id)]
        ) as capt:
            channel.message_post(**self._get_gateway_thread_message_vals())
        if not self.gateway_type:
            self.gateway_type = gateway_channel_id.gateway_id.gateway_type
        notification_vals = {
            "notification_status": "sent",
            "mail_message_id": self.id,
            "gateway_channel_id": channel.id,
            "notification_type": "gateway",
            "gateway_type": gateway_channel_id.gateway_id.gateway_type,
        }
        notification = capt.records
        if notification:
            # Set the same gateway_message_id for both notifications.
            # When the webhook is received, both notifications must be updated.
            # For example, when a message is sent from a document(sale.order),
            # one notification is linked to the document,
            # and another notification is linked to the channel.
            notification_vals["gateway_message_id"] = notification.gateway_message_id
            # If there is a notification with status "exception", set failure details
            if notification.failure_type == "unknown":
                notification_vals["failure_type"] = "unknown"
                notification_vals["notification_status"] = "exception"
                notification_vals["failure_reason"] = notification.failure_reason
        self.env["mail.notification"].create(notification_vals)
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "mail.message/insert",
            {
                "id": self.id,
                "gateway_type": self.gateway_type,
                "notifications": self.sudo()
                .notification_ids._filtered_for_web_client()
                ._notification_format(),
            },
        )
        return {}

    def _get_gateway_thread_message_vals(self):
        return {
            "body": self.body,
            "attachment_ids": self.attachment_ids.ids,
            "subtype_id": self.subtype_id.id,
            "author_id": self.env.user.partner_id.id,
            "gateway_message_id": self.id,
            "message_type": "comment",
        }
