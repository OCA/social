# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import re
import time
import urllib.parse
import uuid
from datetime import datetime

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tools import SQL, email_split

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
        readonly=True,
        store=True,
        compute="_compute_tracking_display_name",
    )
    timestamp = fields.Float(
        string="UTC timestamp", readonly=True, digits="MailTracking Timestamp"
    )
    time = fields.Datetime(readonly=True, index=True)
    date = fields.Date(readonly=True, compute="_compute_date", store=True)
    mail_message_id = fields.Many2one(
        comodel_name="mail.message", readonly=True, index=True
    )
    message_id = fields.Char(compute="_compute_message_id")
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
    error_type = fields.Char(readonly=True)
    error_description = fields.Char(readonly=True)
    bounce_type = fields.Char(readonly=True)
    bounce_description = fields.Char(readonly=True)
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

    @api.depends("mail_message_id")
    def _compute_message_id(self):
        """This helper field will allow us to map the message_id from either the linked
        mail.message or a mass.mailing mail.trace."""
        self.message_id = False
        for tracking in self.filtered("mail_message_id"):
            tracking.message_id = tracking.mail_message_id.message_id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        failed_states = self.env["mail.message"].get_failed_states()
        records.filtered(lambda one: one.state in failed_states).mapped(
            "mail_message_id"
        ).write({"mail_tracking_needs_action": True})
        return records

    def write(self, vals):
        res = super().write(vals)
        state = vals.get("state")
        if state and state in self.env["mail.message"].get_failed_states():
            self.mapped("mail_message_id").write({"mail_tracking_needs_action": True})
        return res

    @api.model
    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
    ):
        """Override that adds specific access rights of mail.tracking.email, to remove
        ids uid could not see according to our custom rules. Please refer to
        _check_access() for more details about those rules.
        """
        query = super()._search(domain, offset, limit, order)
        if not self.env.user.has_group("base.group_system"):
            records = self.browse(query)
            allowed_ids = self._get_allowed_ids(records.ids)
            return self.browse(allowed_ids)._as_query(order)

        return query

    def _make_access_error(self, operation: str) -> AccessError:
        return AccessError(
            _(
                "The requested operation cannot be completed due to security restrictions. "  # noqa: E501
                "Please contact your system administrator.\n\n"
                "(Document type: %(type)s, Operation: %(operation)s)\n\n"
                "Records: %(records)s, User: %(user)s",
                type=self._description,
                operation=operation,
                records=self.ids[:6],
                user=self.env.uid,
            )
        )

    def _get_forbidden_access(self) -> api.Self:
        """Return the subset of ``self`` that does not satisfy the specific
        conditions for messages.
        """

        forbidden = self.browse()
        allowed_ids = self._get_allowed_ids(self.ids)

        trackings_to_check = [
            tracking_id for tracking_id in self.ids if tracking_id not in allowed_ids
        ]

        if not trackings_to_check:
            return forbidden
        forbidden += self.browse(trackings_to_check)
        return forbidden

    def _check_access(self, operation):
        """Access rules of mail.tracking.email:
        - read: if
            - Those with a linked mail.message that the user can read
            - Those with a linked mail.mail that the user can read
            - Those with no message/mail link but a linked partner that the user can
              read.
            - Those with no linked records.
        """
        result = super()._check_access(operation)
        if not self:
            return result

        # discard forbidden records, and check remaining ones
        trackings = self - result[0] if result else self
        if trackings and (forbidden := trackings._get_forbidden_access()):
            if result:
                result = (result[0] + forbidden, result[1])
            else:
                result = (forbidden, lambda: forbidden._make_access_error(operation))
        return result

    def read(self, fields=None, load="_classic_read"):
        """Override to explicitly call check_access, that is not called
        by the ORM. It instead directly fetches ir.rules and apply them.
        """
        self.check_access("read")
        return super().read(fields=fields, load=load)

    def _get_allowed_ids(self, ids):
        allowed_ids = set()
        self.env.cr.execute(
            SQL(
                """ SELECT id, mail_message_id, mail_id, partner_id
                    FROM "mail_tracking_email"
                    WHERE id = ANY (%s)
                """,
                (ids,),
            )
        )
        result = self.env.cr.fetchall()
        for id_, mail_msg_id, mail_id, partner_id in result:
            msg_ids = (
                self.env["mail.message"].search([("id", "=", mail_msg_id)]).ids
                if mail_msg_id
                else []
            )
            mail_ids = (
                self.env["mail.mail"].search([("id", "=", mail_id)]).ids
                if mail_id
                else []
            )
            partner_ids = (
                self.env["res.partner"].search([("id", "=", partner_id)]).ids
                if partner_id
                else []
            )

            if (
                (mail_msg_id in msg_ids)
                or (mail_id in mail_ids)
                or (not any({mail_msg_id, mail_id}) and partner_id in partner_ids)
                or (not any({mail_msg_id, mail_id, partner_id}))
            ):
                allowed_ids.add(id_)
        return allowed_ids

    @api.model
    def email_is_bounced(self, email):
        if not email:
            return False
        res = self.sudo()._email_last_tracking_state(email)
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
        data = self.sudo().read_group(
            [("recipient_address", "=", email.lower())],
            ["recipient_address", "state"],
            ["state"],
        )
        mapped_data = {state["state"]: state["state_count"] for state in data}
        return self.with_context(mt_states=mapped_data).sudo().email_score()

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
            email.recipient_address = False
            recipient_email = email_split(email.recipient)
            if recipient_email:
                email.recipient_address = recipient_email[0].lower()

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
                f"mail/tracking/open/{self.env.cr.dbname}/{self.id}/{self.token}/"
                f"blank.gif"
            )
        else:
            # This is here for compatibility with older records
            path_url = f"mail/tracking/open/{self.env.cr.dbname}/{self.id}/blank.gif"
        track_url = urllib.parse.urljoin(base_url, path_url)
        _logger.debug(f"Sending email will tracking url: {track_url}")
        return f'<img src="{track_url}" alt="" data-odoo-tracking-email="{self.id}"/>'

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
                    "error_smtp_server": smtp_server,
                    "error_type": exception.__class__.__name__,
                    "error_description": tools.exception_to_unicode(exception),
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
            body = tools.mail.append_content_to_html(
                content, tracking_url, plaintext=False, container_tag="div"
            )
            email["body"] = body

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
                    {"notified_partner_ids": [Command.link(self.partner_id.id)]}
                )
            else:
                mail_message.sudo().write(
                    {"partner_ids": [Command.link(self.partner_id.id)]}
                )
        return True

    def _tracking_sent_prepare(self, mail_server, smtp_server, message, message_id):
        self.ensure_one()
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        self._message_partners_check(message, message_id)
        self.sudo().write({"state": "sent"})
        return {
            "recipient": message["To"],
            "timestamp": f"{ts:.6f}",
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
            _logger.info(f"Unknown event type: {event_type}")
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

    # TODO Remove useless method
    @api.model
    def event_process(self, request, post, metadata, event_type=None):
        # Generic event process hook, inherit it and
        # - return 'OK' if processed
        # - return 'NONE' if this request is not for you
        # - return 'ERROR' if any error
        return "NONE"  # pragma: no cover

    def _get_old_mail_tracking_email_domain(self, max_age_days):
        target_write_date = fields.Datetime.subtract(
            fields.Datetime.now(), days=max_age_days
        )
        return [("write_date", "<", target_write_date)]

    @api.autovacuum
    def _gc_mail_tracking_email(self, limit=5000):
        config_max_age_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_tracking.mail_tracking_email_max_age_days")
        )
        try:
            max_age_days = int(config_max_age_days)
        except ValueError:
            max_age_days = 0

        if not max_age_days > 0:
            return False

        domain = self._get_old_mail_tracking_email_domain(max_age_days)
        records_to_delete = self.search(domain, limit=limit).exists()
        if records_to_delete:
            _logger.info(
                "Deleting %s mail.tracking.email records", len(records_to_delete)
            )
            records_to_delete.flush_recordset()
            # Using a direct query to avoid ORM as it causes an issue with
            # a related field mass_mailing_id in customer DB when deleting
            # the records. This might be 14.0 specific, so changing to
            # .unlink() should be tested when forward porting.
            query = "DELETE FROM mail_tracking_email WHERE id IN %s"
            args = (tuple(records_to_delete.ids),)
            self.env.cr.execute(query, args)
            self.invalidate_model()
