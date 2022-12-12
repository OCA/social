# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from collections import namedtuple
from datetime import datetime
from urllib.parse import urljoin

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split

_logger = logging.getLogger(__name__)

MailgunParameters = namedtuple(
    "MailgunParameters",
    (
        "api_key",
        "api_url",
        "domain",
        "validation_key",
        "webhooks_domain",
        "webhook_signing_key",
    ),
)


class EventNotFoundWarning(Warning):
    pass


class MailTrackingEmail(models.Model):
    _inherit = "mail.tracking.email"

    def _country_search(self, country_code):
        country = False
        if country_code:
            country = self.env["res.country"].search(
                [("code", "=", country_code.upper())]
            )
        if country:
            return country.id
        return False

    @api.model
    def _mailgun_event2type(self, event, default="UNKNOWN"):
        """Return the ``mail.tracking.event`` equivalent event

        Args:
            event: Mailgun event response from API.
            default: Value to return when not found.
        """
        # Mailgun event type: tracking event type
        equivalents = {
            "delivered": "delivered",
            "opened": "open",
            "clicked": "click",
            "unsubscribed": "unsub",
            "complained": "spam",
            "accepted": "sent",
            "failed": (
                "hard_bounce" if event.get("severity") == "permanent" else "soft_bounce"
            ),
            "rejected": "reject",
        }
        return equivalents.get(event.get("event"), default)

    @api.model
    def _mailgun_values(self):
        icp = self.env["ir.config_parameter"].sudo()
        api_key = icp.get_param("mailgun.apikey")
        if not api_key:
            raise ValidationError(_("There is no Mailgun API key!"))
        api_url = icp.get_param("mailgun.api_url", "https://api.mailgun.net/v3")
        catchall_domain = icp.get_param("mail.catchall.domain")
        domain = icp.get_param("mailgun.domain", catchall_domain)
        if not domain:
            raise ValidationError(_("A Mailgun domain value is needed!"))
        validation_key = icp.get_param("mailgun.validation_key")
        web_base_url = icp.get_param("web.base.url")
        webhooks_domain = icp.get_param("mailgun.webhooks_domain", web_base_url)
        webhook_signing_key = icp.get_param("mailgun.webhook_signing_key")
        return MailgunParameters(
            api_key,
            api_url,
            domain,
            validation_key,
            webhooks_domain,
            webhook_signing_key,
        )

    def _mailgun_metadata(self, mailgun_event_type, event, metadata):
        # Get Mailgun timestamp when found
        ts = event.get("timestamp", False)
        try:
            ts = float(ts)
        except Exception:
            ts = False
        if ts:
            dt = datetime.utcfromtimestamp(ts)
            metadata.update(
                {
                    "timestamp": ts,
                    "time": fields.Datetime.to_string(dt),
                    "date": fields.Date.to_string(dt),
                    "mailgun_id": event.get("id", False),
                }
            )
        # Common field mapping
        mapping = {
            "recipient": "recipient",
            "ip": "ip",
            "user_agent": "user-agent",
            "os_family": "client-os",
            "ua_family": "client-name",
            "ua_type": "client-type",
            "url": "url",
        }
        for k, v in mapping.items():
            if event.get(v, False):
                metadata[k] = event[v]
        # Special field mapping
        metadata.update(
            {
                "mobile": event.get("device-type") in {"mobile", "tablet"},
                "user_country_id": self._country_search(event.get("country", False)),
            }
        )
        # Mapping for special events
        if mailgun_event_type == "failed":
            delivery_status = event.get("delivery-status", {})
            metadata.update(
                {
                    "error_type": delivery_status.get("code", False),
                    "error_description": delivery_status.get("message", False),
                    "error_details": delivery_status.get("description", False),
                }
            )
        elif mailgun_event_type == "rejected":
            reject = event.get("reject", {})
            metadata.update(
                {
                    "error_type": "rejected",
                    "error_description": reject.get("reason", False),
                    "error_details": reject.get("description", False),
                }
            )
        elif mailgun_event_type == "complained":
            metadata.update(
                {
                    "error_type": "spam",
                    "error_description": "Recipient '%s' mark this email as spam"
                    % event.get("recipient", False),
                }
            )
        return metadata

    @api.model
    def _mailgun_event_process(self, event_data, metadata):
        """Retrieve (and maybe create) mailgun event from API data payload.

        In https://documentation.mailgun.com/en/latest/api-events.html#event-structure
        you can read the event payload format as obtained from webhooks or calls to API.
        """
        if event_data["user-variables"]["odoo_db"] != self.env.cr.dbname:
            raise ValidationError(_("Wrong database for event!"))
        # Do nothing if event was already processed
        mailgun_id = event_data["id"]
        db_event = self.env["mail.tracking.event"].search(
            [("mailgun_id", "=", mailgun_id)], limit=1
        )
        if db_event:
            _logger.debug("Mailgun event already found in DB: %s", mailgun_id)
            return db_event
        # Do nothing if tracking email for event is not found
        message_id = event_data["message"]["headers"]["message-id"]
        recipient = event_data["recipient"]
        tracking_email = self.browse(
            int(event_data["user-variables"]["tracking_email_id"])
        )
        mailgun_event_type = event_data["event"]
        # Process event
        state = self._mailgun_event2type(event_data, mailgun_event_type)
        metadata = self._mailgun_metadata(mailgun_event_type, event_data, metadata)
        _logger.info(
            "Importing mailgun event %s (%s message %s for %s)",
            mailgun_id,
            mailgun_event_type,
            message_id,
            recipient,
        )
        tracking_email.event_create(state, metadata)

    def action_manual_check_mailgun(self):
        """Manual check against Mailgun API

        API Documentation:
        https://documentation.mailgun.com/en/latest/api-events.html
        """
        api_key, api_url, domain, *__ = self._mailgun_values()
        for tracking in self:
            if not tracking.mail_message_id:
                raise UserError(_("There is no tracked message!"))
            message_id = tracking.mail_message_id.message_id.replace("<", "").replace(
                ">", ""
            )
            events = []
            url = urljoin(api_url, "/v3/%s/events" % domain)
            params = {
                "begin": tracking.timestamp,
                "ascending": "yes",
                "message-id": message_id,
                "recipient": email_split(tracking.recipient)[0],
            }
            while url:
                res = requests.get(
                    url,
                    auth=("api", api_key),
                    params=params,
                )
                if not res or res.status_code != 200:
                    raise UserError(_("Couldn't retrieve Mailgun information"))
                iter_events = res.json().get("items", [])
                if not iter_events:
                    # Loop no more
                    break
                events.extend(iter_events)
                # Loop over pagination
                url = res.json().get("paging", {}).get("next")
            if not events:
                raise UserError(_("Event information not longer stored"))
            for event in events:
                self.sudo()._mailgun_event_process(event, {})
