# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re
import time
import urllib.parse
import uuid
from datetime import datetime

from odoo import api, fields, models, tools

_logger = logging.getLogger(__name__)

EVENT_OPEN_DELTA = 10  # seconds
EVENT_CLICK_DELTA = 5  # seconds


class MailTrackingEmail(models.Model):
    _name = "mail.tracking.email"
    _order = "time desc"
    _rec_name = "display_name"
    _description = "MailTracking email"

    # This table is going to grow fast and to infinite, so we index:
    # - name: Search in tree view
    # - time: default order fields
    # - recipient_address: Used for email_store calculation (non-store)
    # - state: Search and group_by in tree view
    name = fields.Char(string="Subject", readonly=True, index=True)
    display_name = fields.Char(
        string="Display name",
        readonly=True,
        store=True,
        compute="_compute_tracking_display_name",
    )
    timestamp = fields.Float(
        string="UTC timestamp", readonly=True, digits="MailTracking Timestamp"
    )
    time = fields.Datetime(string="Time", readonly=True, index=True)
    date = fields.Date(
        string="Date", readonly=True, compute="_compute_date", store=True
    )
    mail_message_id = fields.Many2one(
        string="Message", comodel_name="mail.message", readonly=True, index=True
    )
    mail_id = fields.Many2one(string="Email", comodel_name="mail.mail", readonly=True)
    partner_id = fields.Many2one(
        string="Partner", comodel_name="res.partner", readonly=True
    )
    recipient = fields.Char(string="Recipient email", readonly=True)
    recipient_address = fields.Char(
        string="Recipient email address",
        readonly=True,
        store=True,
        compute="_compute_recipient_address",
        index=True,
    )
    sender = fields.Char(string="Sender email", readonly=True)
    state = fields.Selection(
        [
            ("error", "Error"),
            ("deferred", "Deferred"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("opened", "Opened"),
            ("rejected", "Rejected"),
            ("spam", "Spam"),
            ("unsub", "Unsubscribed"),
            ("bounced", "Bounced"),
            ("soft-bounced", "Soft bounced"),
        ],
        string="State",
        index=True,
        readonly=True,
        default=False,
        help=" * The 'Error' status indicates that there was an error "
        "when trying to sent the email, for example, "
        "'No valid recipient'\n"
        " * The 'Sent' status indicates that message was succesfully "
        "sent via outgoing email server (SMTP).\n"
        " * The 'Delivered' status indicates that message was "
        "succesfully delivered to recipient Mail Exchange (MX) server.\n"
        " * The 'Opened' status indicates that message was opened or "
        "clicked by recipient.\n"
        " * The 'Rejected' status indicates that recipient email "
        "address is blacklisted by outgoing email server (SMTP). "
        "It is recomended to delete this email address.\n"
        " * The 'Spam' status indicates that outgoing email "
        "server (SMTP) consider this message as spam.\n"
        " * The 'Unsubscribed' status indicates that recipient has "
        "requested to be unsubscribed from this message.\n"
        " * The 'Bounced' status indicates that message was bounced "
        "by recipient Mail Exchange (MX) server.\n"
        " * The 'Soft bounced' status indicates that message was soft "
        "bounced by recipient Mail Exchange (MX) server.\n",
    )
    error_smtp_server = fields.Char(string="Error SMTP server", readonly=True)
    error_type = fields.Char(string="Error type", readonly=True)
    error_description = fields.Char(string="Error description", readonly=True)
    bounce_type = fields.Char(string="Bounce type", readonly=True)
    bounce_description = fields.Char(string="Bounce description", readonly=True)
    tracking_event_ids = fields.One2many(
        string="Tracking events",
        comodel_name="mail.tracking.event",
        inverse_name="tracking_email_id",
        readonly=True,
    )
    # Token isn't generated here to have compatibility with older trackings.
    # New trackings have token and older not
    token = fields.Char(
        string="Security Token",
        readonly=True,
        default=lambda s: uuid.uuid4().hex,
        groups="base.group_system",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        failed_states = self.env["mail.message"].get_failed_states()
        records.filtered(lambda one: one.state in failed_states).mapped(
            "mail_message_id"
        ).write({"mail_tracking_needs_action": True})
        return records

    def write(self, vals):
        super().write(vals)
        state = vals.get("state")
        if state and state in self.env["mail.message"].get_failed_states():
            self.mapped("mail_message_id").write({"mail_tracking_needs_action": True})

    @api.model
    def email_is_bounced(self, email):
        if not email:
            return False
        res = self._email_last_tracking_state(email)
        return res and res[0].get("state", "") in {
            "rejected",
            "error",
            "spam",
            "bounced",
        }

    @api.model
    def _email_last_tracking_state(self, email):
        return self.search_read(
            [("recipient_address", "=", email.lower())],
            ["state"],
            limit=1,
            order="time DESC",
        )

    @api.model
    def email_score_from_email(self, email):
        if not email:
            return 0.0
        data = self.read_group(
            [("recipient_address", "=", email.lower())],
            ["recipient_address", "state"],
            ["state"],
        )
        mapped_data = {state["state"]: state["state_count"] for state in data}
        return self.with_context(mt_states=mapped_data).email_score()

    @api.model
    def _email_score_weights(self):
        """Default email score weights. Ready to be inherited"""
        return {
            "error": -50.0,
            "rejected": -25.0,
            "spam": -25.0,
            "bounced": -25.0,
            "soft-bounced": -10.0,
            "unsub": -10.0,
            "delivered": 1.0,
            "opened": 5.0,
        }

    def email_score(self):
        """Default email score algorimth. Ready to be inherited
        It can receive a recordset or mapped states dictionary via context.
        Must return a value beetwen 0.0 and 100.0
        - Bad reputation: Value between 0 and 50.0
        - Unknown reputation: Value 50.0
        - Good reputation: Value between 50.0 and 100.0
        """
        weights = self._email_score_weights()
        score = 50.0
        states = self.env.context.get("mt_states", False)
        if states:
            for state in states.keys():
                score += weights.get(state, 0.0) * states[state]
        else:
            for tracking in self:
                score += weights.get(tracking.state, 0.0)
        if score > 100.0:
            score = 100.0
        elif score < 0.0:
            score = 0.0
        return score

    @api.depends("recipient")
    def _compute_recipient_address(self):
        for email in self:
            is_empty_recipient = not email.recipient or "<False>" in email.recipient
            if not is_empty_recipient:
                matches = re.search(r"<(.*@.*)>", email.recipient)
                if matches:
                    email.recipient_address = matches.group(1).lower()
                else:
                    email.recipient_address = email.recipient.lower()
            else:
                email.recipient_address = False

    @api.depends("name", "recipient")
    def _compute_tracking_display_name(self):
        for email in self:
            parts = [email.name or ""]
            if email.recipient:
                parts.append(email.recipient)
            email.display_name = " - ".join(parts)

    @api.depends("time")
    def _compute_date(self):
        for email in self:
            email.date = fields.Date.to_string(fields.Date.from_string(email.time))

    def _get_mail_tracking_img(self):
        m_config = self.env["ir.config_parameter"]
        base_url = m_config.get_param("mail_tracking.base.url") or m_config.get_param(
            "web.base.url"
        )
        if self.token:
            path_url = (
                "mail/tracking/open/%(db)s/%(tracking_email_id)s/%(token)s/"
                "blank.gif"
                % {
                    "db": self.env.cr.dbname,
                    "tracking_email_id": self.id,
                    "token": self.token,
                }
            )
        else:
            # This is here for compatibility with older records
            path_url = "mail/tracking/open/{db}/{tracking_email_id}/blank.gif".format(
                db=self.env.cr.dbname, tracking_email_id=self.id
            )
        track_url = urllib.parse.urljoin(base_url, path_url)
        return (
            '<img src="%(url)s" alt="" '
            'data-odoo-tracking-email="%(tracking_email_id)s"/>'
            % {"url": track_url, "tracking_email_id": self.id}
        )

    def _partners_email_bounced_set(self, reason, event=None):
        recipients = []
        if event and event.recipient_address:
            recipients.append(event.recipient_address)
        else:
            recipients = [x for x in self.mapped("recipient_address") if x]
        for recipient in recipients:
            self.env["res.partner"].search(
                [("email", "=ilike", recipient)]
            ).email_bounced_set(self, reason, event=event)

    def smtp_error(self, mail_server, smtp_server, exception):
        values = {"state": "error"}
        IrMailServer = self.env["ir.mail_server"]
        if (
            str(exception) == IrMailServer.NO_VALID_RECIPIENT
            and not self.recipient_address
        ):
            values.update(
                {
                    "error_type": "no_recipient",
                    "error_description": "The partner doesn't have a defined email",
                }
            )
        else:
            values.update(
                {
                    "error_smtp_server": tools.ustr(smtp_server),
                    "error_type": exception.__class__.__name__,
                    "error_description": tools.ustr(exception),
                }
            )
            self.sudo()._partners_email_bounced_set("error")
        self.sudo().write(values)

    def tracking_img_add(self, email):
        self.ensure_one()
        tracking_url = self._get_mail_tracking_img()
        if tracking_url:
            content = email.get("body", "")
            content = re.sub(
                r'<img[^>]*data-odoo-tracking-email=["\'][0-9]*["\'][^>]*>', "", content
            )
            body = tools.append_content_to_html(
                content, tracking_url, plaintext=False, container_tag="div"
            )
            email["body"] = body
        return email

    def _message_partners_check(self, message, message_id):
        if not self.mail_message_id.exists():  # pragma: no cover
            return True
        mail_message = self.mail_message_id
        partners = mail_message.notified_partner_ids | mail_message.partner_ids
        if self.partner_id and self.partner_id not in partners:
            # If mail_message haven't tracking partner, then
            # add it in order to see his tracking status in chatter
            if mail_message.subtype_id:
                mail_message.sudo().write(
                    {"notified_partner_ids": [(4, self.partner_id.id)]}
                )
            else:
                mail_message.sudo().write({"partner_ids": [(4, self.partner_id.id)]})
        return True

    def _tracking_sent_prepare(self, mail_server, smtp_server, message, message_id):
        self.ensure_one()
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        self._message_partners_check(message, message_id)
        self.sudo().write({"state": "sent"})
        return {
            "recipient": message["To"],
            "timestamp": "%.6f" % ts,
            "time": fields.Datetime.to_string(dt),
            "tracking_email_id": self.id,
            "event_type": "sent",
            "smtp_server": smtp_server,
        }

    def _event_prepare(self, event_type, metadata):
        self.ensure_one()
        m_event = self.env["mail.tracking.event"]
        method = getattr(m_event, "process_" + event_type, None)
        if method and callable(method):
            return method(self, metadata)
        else:  # pragma: no cover
            _logger.info("Unknown event type: %s" % event_type)
        return False

    def _concurrent_events(self, event_type, metadata):
        m_event = self.env["mail.tracking.event"]
        self.ensure_one()
        concurrent_event_ids = False
        if event_type in {"open", "click"}:
            ts = metadata.get("timestamp", time.time())
            delta = EVENT_OPEN_DELTA if event_type == "open" else EVENT_CLICK_DELTA
            domain = [
                ("timestamp", ">=", ts - delta),
                ("timestamp", "<=", ts + delta),
                ("tracking_email_id", "=", self.id),
                ("event_type", "=", event_type),
            ]
            if event_type == "click":
                domain.append(("url", "=", metadata.get("url", False)))
            concurrent_event_ids = m_event.search(domain)
        return concurrent_event_ids

    def event_create(self, event_type, metadata):
        event_ids = self.env["mail.tracking.event"]
        for tracking_email in self:
            other_ids = tracking_email._concurrent_events(event_type, metadata)
            if not other_ids:
                vals = tracking_email._event_prepare(event_type, metadata)
                if vals:
                    events = event_ids.sudo().create(vals)
                    if event_type in {"hard_bounce", "spam", "reject"}:
                        for event in events:
                            self.sudo()._partners_email_bounced_set(
                                event_type, event=event
                            )
                    event_ids += events
            else:
                _logger.debug("Concurrent event '%s' discarded", event_type)
        return event_ids

    @api.model
    def event_process(self, request, post, metadata, event_type=None):
        # Generic event process hook, inherit it and
        # - return 'OK' if processed
        # - return 'NONE' if this request is not for you
        # - return 'ERROR' if any error
        return "NONE"  # pragma: no cover
