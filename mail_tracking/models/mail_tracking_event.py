# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import time
from datetime import datetime

from odoo import api, fields, models


class MailTrackingEvent(models.Model):
    _name = "mail.tracking.event"
    _order = "timestamp desc"
    _rec_name = "event_type"
    _description = "MailTracking event"

    recipient = fields.Char(string="Recipient", readonly=True)
    recipient_address = fields.Char(
        string="Recipient email address",
        readonly=True,
        store=True,
        compute="_compute_recipient_address",
        index=True,
    )
    timestamp = fields.Float(
        string="UTC timestamp", readonly=True, digits="MailTracking Timestamp"
    )
    time = fields.Datetime(string="Time", readonly=True)
    date = fields.Date(
        string="Date", readonly=True, compute="_compute_date", store=True
    )
    tracking_email_id = fields.Many2one(
        string="Message",
        readonly=True,
        required=True,
        ondelete="cascade",
        comodel_name="mail.tracking.email",
        index=True,
    )
    event_type = fields.Selection(
        string="Event type",
        selection=[
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("deferral", "Deferral"),
            ("hard_bounce", "Hard bounce"),
            ("soft_bounce", "Soft bounce"),
            ("open", "Open"),
            ("click", "Clicked"),
            ("spam", "Spam"),
            ("unsub", "Unsubscribed"),
            ("reject", "Rejected"),
        ],
        readonly=True,
    )
    smtp_server = fields.Char(string="SMTP server", readonly=True)
    url = fields.Char(string="Clicked URL", readonly=True)
    ip = fields.Char(string="User IP", readonly=True)
    user_agent = fields.Char(string="User agent", readonly=True)
    mobile = fields.Boolean(string="Is mobile?", readonly=True)
    os_family = fields.Char(string="Operating system family", readonly=True)
    ua_family = fields.Char(string="User agent family", readonly=True)
    ua_type = fields.Char(string="User agent type", readonly=True)
    user_country_id = fields.Many2one(
        string="User country", readonly=True, comodel_name="res.country"
    )
    error_type = fields.Char(string="Error type", readonly=True)
    error_description = fields.Char(string="Error description", readonly=True)
    error_details = fields.Text(string="Error details", readonly=True)

    @api.depends("recipient")
    def _compute_recipient_address(self):
        for email in self:
            if email.recipient:
                matches = re.search(r"<(.*@.*)>", email.recipient)
                if matches:
                    email.recipient_address = matches.group(1).lower()
                else:
                    email.recipient_address = email.recipient.lower()
            else:
                email.recipient_address = False

    @api.depends("time")
    def _compute_date(self):
        for email in self:
            email.date = fields.Date.to_string(fields.Date.from_string(email.time))

    def _process_data(self, tracking_email, metadata, event_type, state):
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        return {
            "recipient": metadata.get("recipient", tracking_email.recipient),
            "timestamp": metadata.get("timestamp", ts),
            "time": metadata.get("time", fields.Datetime.to_string(dt)),
            "date": metadata.get("date", fields.Date.to_string(dt)),
            "tracking_email_id": tracking_email.id,
            "event_type": event_type,
            "ip": metadata.get("ip", False),
            "url": metadata.get("url", False),
            "user_agent": metadata.get("user_agent", False),
            "mobile": metadata.get("mobile", False),
            "os_family": metadata.get("os_family", False),
            "ua_family": metadata.get("ua_family", False),
            "ua_type": metadata.get("ua_type", False),
            "user_country_id": metadata.get("user_country_id", False),
            "error_type": metadata.get("error_type", False),
            "error_description": metadata.get("error_description", False),
            "error_details": metadata.get("error_details", False),
        }

    def _process_status(self, tracking_email, metadata, event_type, state):
        tracking_email.sudo().write({"state": state})
        return self._process_data(tracking_email, metadata, event_type, state)

    def _process_bounce(self, tracking_email, metadata, event_type, state):
        tracking_email.sudo().write(
            {
                "state": state,
                "bounce_type": metadata.get("bounce_type", False),
                "bounce_description": metadata.get("bounce_description", False),
            }
        )
        return self._process_data(tracking_email, metadata, event_type, state)

    @api.model
    def process_delivered(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "delivered", "delivered")

    @api.model
    def process_deferral(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "deferral", "deferred")

    @api.model
    def process_hard_bounce(self, tracking_email, metadata):
        return self._process_bounce(tracking_email, metadata, "hard_bounce", "bounced")

    @api.model
    def process_soft_bounce(self, tracking_email, metadata):
        return self._process_bounce(
            tracking_email, metadata, "soft_bounce", "soft-bounced"
        )

    @api.model
    def process_open(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "open", "opened")

    @api.model
    def process_click(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "click", "opened")

    @api.model
    def process_spam(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "spam", "spam")

    @api.model
    def process_unsub(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "unsub", "unsub")

    @api.model
    def process_reject(self, tracking_email, metadata):
        return self._process_status(tracking_email, metadata, "reject", "rejected")
