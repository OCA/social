# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from xmlrpc.client import DateTime

from odoo import api, fields, models


class MailChannel(models.Model):
    _inherit = "mail.channel"

    token = fields.Char()
    broker_id = fields.Many2one("mail.broker")
    broker_message_ids = fields.One2many(
        "mail.message.broker",
        inverse_name="channel_id",
    )
    last_message_date = fields.Datetime(
        compute="_compute_message_data",
        store=True,
    )
    public = fields.Selection(
        selection_add=[("broker", "Broker")], ondelete={"broker": "set default"}
    )
    channel_type = fields.Selection(
        selection_add=[("broker", "Broker")], ondelete={"broker": "set default"}
    )
    broker_unread = fields.Integer(
        compute="_compute_message_data",
        store=True,
    )
    broker_token = fields.Char(related="broker_id.token", store=True, required=False)
    show_on_app = fields.Boolean()
    broker_partner_id = fields.Many2one("res.partner")

    def message_fetch(self, domain=False, limit=30):
        self.ensure_one()
        if not domain:
            domain = []
        return (
            self.env["mail.message"]
            .search([("broker_channel_id", "=", self.id)] + domain, limit=limit)
            .message_format()
        )

    @api.depends(
        "message_ids",
        "message_ids.date",
        "message_ids.broker_unread",
    )
    def _compute_message_data(self):
        for r in self:
            r.last_message_date = (
                self.env["mail.message"]
                .search(
                    [("broker_channel_id", "=", r.id)],
                    limit=1,
                    order="date DESC",
                )
                .date
            )
            r.broker_unread = self.env["mail.message"].search_count(
                [("broker_channel_id", "=", r.id), ("broker_unread", "=", True)]
            )

    def _get_thread_data(self):
        return {
            "id": "broker_thread_%s" % self.id,
            "res_id": self.id,
            "name": self.name,
            "last_message_date": self.last_message_date,
            "channel_type": "broker_thread",
            "unread": self.broker_unread,
            "broker_id": self.broker_id.id,
        }

    def _broker_message_post_vals(
        self,
        body,
        subtype_id=False,
        author_id=False,
        date=False,
        message_id=False,
        **kwargs
    ):
        if not subtype_id:
            subtype = kwargs.get("subtype") or "mt_note"
            if "." not in subtype:
                subtype = "mail.%s" % subtype
            subtype_id = self.env["ir.model.data"].xmlid_to_res_id(subtype)
        vals = {
            "channel_id": self.id,
            "channel_ids": [(4, self.id)],
            "body": body,
            "subtype_id": subtype_id,
            "model": self._name,
            "res_id": self.id,
            "broker_type": self.broker_id.broker_type,
        }
        if author_id:
            vals["author_id"] = author_id
        if date:
            if isinstance(date, DateTime):
                date = datetime.strptime(str(date), "%Y%m%dT%H:%M:%S")
            vals["date"] = date
        if message_id:
            vals["message_id"] = message_id
        vals["broker_unread"] = kwargs.get("broker_unread", False)
        vals["attachment_ids"] = []
        for attachment_id in kwargs.get("attachment_ids", []):
            vals["attachment_ids"].append((4, attachment_id))
        for name, content, mimetype in kwargs.get("attachments", []):
            vals["attachment_ids"].append(
                (
                    0,
                    0,
                    {
                        "name": name,
                        "datas": content.encode("utf-8"),
                        "type": "binary",
                        "description": name,
                        "mimetype": mimetype,
                    },
                )
            )
        return vals

    @api.returns("mail.message.broker", lambda value: value.id)
    def message_post_broker(self, body=False, broker_type=False, **kwargs):
        self.ensure_one()
        if (
            not body
            and not kwargs.get("attachments")
            and not kwargs.get("attachment_ids")
        ):
            return False
        vals = self._broker_message_post_vals(
            body, broker_unread=True, author_id=self.broker_partner_id.id, **kwargs
        )
        vals["state"] = "received"
        vals["broker_type"] = broker_type
        return self.env["mail.message.broker"].create(vals)

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *args, **kwargs):
        message = super().message_post(*args, **kwargs)
        if self.broker_id:
            self.env["mail.message.broker"].create(
                {
                    "mail_message_id": message.id,
                    "channel_id": self.id,
                }
            ).send()
        return message

    @api.model
    def channel_fetch_slot(self):
        result = super().channel_fetch_slot()
        broker_channels = self.env["mail.channel"].search([("public", "=", "broker")])
        result["channel_channel"] += broker_channels.channel_info()
        return result

    def channel_info(self, *args, **kwargs):
        result = super().channel_info(*args, **kwargs)
        for channel, channel_info in zip(self, result):
            channel_info["broker_id"] = (
                channel.broker_id and channel.broker_id.id or False
            )
            channel_info["broker_unread_counter"] = channel.broker_unread
        return result

    @api.model_create_multi
    def create(self, vals_list):
        channels = super().create(vals_list)
        notifications = []
        for channel in channels:
            if channel.show_on_app and channel.broker_id.show_on_app:
                notifications.append(
                    (
                        (self._cr.dbname, "mail.broker", channel.broker_id.id),
                        {"thread": channel._get_thread_data()},
                    )
                )
        if notifications:
            self.env["bus.bus"].sendmany(notifications)
        return channels

    @api.returns("mail.message.broker", lambda value: value.id)
    def broker_message_post(self, body=False, **kwargs):
        self.ensure_one()
        if not body and not kwargs.get("attachment_ids"):
            return
        message = (
            self.with_context(do_not_notify=True)
            .env["mail.message.broker"]
            .create(self._broker_message_post_vals(body, **kwargs))
        )
        message.send()
        self.env["bus.bus"].sendone(
            (self._cr.dbname, "mail.broker", message.channel_id.broker_id.id),
            {"message": message.mail_message_id.message_format()[0]},
        )
        return message
