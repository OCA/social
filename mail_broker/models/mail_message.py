# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class MailMessage(models.Model):

    _inherit = "mail.message"

    broker_type = fields.Selection(
        selection=lambda r: r.env["mail.broker"]._fields["broker_type"].selection
    )
    broker_notification_ids = fields.One2many(
        "mail.notification",
        inverse_name="mail_message_id",
        domain=[("notification_type", "=", "broker")],
    )
    broker_channel_ids = fields.Many2many(
        "res.partner.broker.channel", compute="_compute_broker_channel_ids"
    )
    broker_channel_data = fields.Json(compute="_compute_broker_channel_ids")
    broker_message_ids = fields.One2many(
        "mail.message", inverse_name="broker_message_id"
    )
    broker_message_id = fields.Many2one("mail.message")
    broker_thread_data = fields.Json(compute="_compute_broker_thread_data")

    @api.depends("broker_message_id")
    def _compute_broker_thread_data(self):
        for record in self:
            broker_thread_data = {}
            if record.broker_message_id:
                broker_thread_data.update(
                    {
                        "name": record.broker_message_id.record_name,
                        "id": record.broker_message_id.res_id,
                        "model": record.broker_message_id.model,
                    }
                )
            record.broker_thread_data = broker_thread_data

    @api.depends("notification_ids", "broker_message_ids")
    def _compute_broker_channel_ids(self):
        for record in self:
            if self.env.user.has_group("mail_broker.broker_user"):
                channels = record.notification_ids.res_partner_id.broker_channel_ids.filtered(
                    lambda r: (r.broker_token, r.broker_id.id)
                    not in [
                        (
                            notification.broker_channel_id.token,
                            notification.broker_channel_id.broker_id.id,
                        )
                        for notification in record.broker_message_ids.broker_notification_ids
                    ]
                )
            else:
                channels = self.env["res.partner.broker.channel"]
            record.broker_channel_ids = channels
            record.broker_channel_data = {
                "channels": channels.ids,
                "partners": channels.partner_id.ids,
            }

    @api.depends("broker_notification_ids")
    def _compute_broker_channel_id(self):
        for rec in self:
            if rec.broker_notification_ids:
                rec.broker_channel_id = rec.broker_notification_ids[0].broker_channel_id

    def _get_message_format_fields(self):
        result = super()._get_message_format_fields()
        result.append("broker_type")
        result.append("broker_channel_data")
        result.append("broker_thread_data")
        return result

    def _send_to_broker_thread(self, broker_channel_id):
        chat_id = broker_channel_id.broker_id._get_channel_id(
            broker_channel_id.broker_token
        )
        channel = self.env["mail.channel"].browse(chat_id)
        channel.message_post(**self._get_broker_thread_message_vals())
        self.env["mail.notification"].create(
            {
                "notification_status": "sent",
                "mail_message_id": self.id,
                "broker_channel_id": channel.id,
                "notification_type": "broker",
                "broker_type": broker_channel_id.broker_id.broker_type,
            }
        )
        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "mail.message/insert",
            {
                "id": self.id,
                "notifications": self.sudo()
                .notification_ids._filtered_for_web_client()
                ._notification_format(),
            },
        )
        return {}

    def _get_broker_thread_message_vals(self):
        return {
            "body": self.body,
            "attachment_ids": self.attachment_ids.ids,
            "subtype_id": self.subtype_id.id,
            "author_id": self.env.user.partner_id.id,
            "broker_message_id": self.id,
            "message_type": "comment",
        }
