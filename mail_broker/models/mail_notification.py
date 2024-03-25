# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailNotification(models.Model):
    _inherit = "mail.notification"

    broker_channel_id = fields.Many2one("mail.channel")
    notification_type = fields.Selection(
        selection_add=[("broker", "Broker")], ondelete={"broker": "cascade"}
    )
    broker_message_id = fields.Char(readonly=True)
    broker_failure_reason = fields.Text(
        readonly=1,
        help="Failure reason. This is usually the exception thrown by the"
        " email server, stored to ease the debugging of mailing issues.",
    )
    broker_type = fields.Selection(
        selection=lambda r: r.env["mail.broker"]._fields["broker_type"].selection
    )

    def _notification_format(self):
        result = super()._notification_format()
        for record, formatted_value in zip(self, result):
            formatted_value["broker_type"] = record.broker_type
            formatted_value["channel_name"] = record.broker_channel_id.name
        return result

    def send_broker(self, auto_commit=False, raise_exception=False, parse_mode="HTML"):
        for record in self:
            broker = record.broker_channel_id.broker_id
            self.env["mail.broker.%s" % broker.broker_type]._send(
                broker,
                record,
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                parse_mode=parse_mode,
            )
