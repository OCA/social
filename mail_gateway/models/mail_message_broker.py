# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailMessageBroker(models.Model):
    _name = "mail.message.broker"
    _description = "Broker Message"
    _inherits = {"mail.message": "mail_message_id"}
    _order = "id desc"
    _rec_name = "subject"

    # content
    mail_message_id = fields.Many2one(
        "mail.message",
        "Mail Message",
        required=True,
        ondelete="cascade",
        index=True,
        auto_join=True,
    )
    message_id = fields.Char(readonly=True)
    channel_id = fields.Many2one(
        "mail.broker.channel", required=True, ondelete="cascade"
    )
    state = fields.Selection(
        [
            ("outgoing", "Outgoing"),
            ("sent", "Sent"),
            ("exception", "Delivery Failed"),
            ("cancel", "Cancelled"),
            ("received", "Received"),
        ],
        "Status",
        readonly=True,
        copy=False,
        default="outgoing",
    )
    failure_reason = fields.Text(
        "Failure Reason",
        readonly=1,
        help="Failure reason. This is usually the exception thrown by the"
        " email server, stored to ease the debugging of mailing issues.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        if self.env.context.get("notify_broker", False):
            notifications = []
            for message in messages:
                notifications.append(
                    [
                        (
                            self._cr.dbname,
                            "mail.broker",
                            message.channel_id.broker_id.id,
                        ),
                        {"message": message.mail_message_id.message_format()[0]},
                    ]
                )
            self.env["bus.bus"].sendmany(notifications)
        return messages

    def send(self, auto_commit=False, raise_exception=False, parse_mode="HTML"):
        for record in self:
            broker = record.channel_id.broker_id
            with broker.work_on(broker._name) as work:
                work.component(usage=broker.broker_type)._send(
                    record,
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    parse_mode=parse_mode,
                )

    def mark_outgoing(self):
        return self.write({"state": "outgoing"})

    def cancel(self):
        return self.write({"state": "cancel"})
