# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):

    _inherit = "mail.message"

    broker_channel_id = fields.Many2one(
        "mail.broker.channel",
        readonly=True,
        compute="_compute_broker_channel_id",
        store=True,
    )
    broker_unread = fields.Boolean(default=False)
    broker_type = fields.Selection(
        selection=lambda r: r.env["mail.broker"]._fields["broker_type"].selection
    )
    broker_notification_ids = fields.One2many(
        "mail.message.broker", inverse_name="mail_message_id"
    )

    @api.depends("broker_notification_ids")
    def _compute_broker_channel_id(self):
        for rec in self:
            if rec.broker_notification_ids:
                rec.broker_channel_id = rec.broker_notification_ids[0].channel_id

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        result = super()._message_read_dict_postprocess(messages, message_tree)
        for message_dict in messages:
            message_id = message_dict.get("id")
            message = message_tree[message_id]
            notifications = message.broker_notification_ids
            if notifications:
                message_dict.update(
                    {
                        "broker_channel_id": message.broker_channel_id.id,
                        "broker_unread": message.broker_unread,
                        "customer_status": "received"
                        if all(d.state == "received" for d in notifications)
                        else message_dict.get("customer_status", False),
                    }
                )
        return result

    def set_message_done(self):
        self.write({"broker_unread": False})
        return super().set_message_done()
