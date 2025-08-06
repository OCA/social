# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailNotification(models.Model):
    _inherit = "mail.notification"

    gateway_channel_id = fields.Many2one("discuss.channel")
    notification_type = fields.Selection(
        selection_add=[("gateway", "Gateway")], ondelete={"gateway": "cascade"}
    )
    gateway_message_id = fields.Char(readonly=True)
    gateway_failure_reason = fields.Text(
        readonly=True,
        help="Failure reason. This is usually the exception thrown by the"
        " email server, stored to ease the debugging of mailing issues.",
    )
    gateway_type = fields.Selection(
        selection=lambda r: r.env["mail.gateway"]._fields["gateway_type"].selection
    )

    def _set_read_gateway(self):
        self.sudo().write({"is_read": True, "read_date": fields.Datetime.now()})

    def _to_store(self, store: Store, /):
        result = super()._to_store(store)
        for record in self:
            store.add(
                record,
                {
                    "gateway_type": record.gateway_type,
                    "channel_name": record.gateway_channel_id.name,
                },
            )
        return result

    def send_gateway(self, auto_commit=False, raise_exception=False, parse_mode="HTML"):
        for record in self:
            gateway = record.gateway_channel_id.gateway_id
            self.env[f"mail.gateway.{gateway.gateway_type}"]._send(
                gateway,
                record,
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                parse_mode=parse_mode,
            )
