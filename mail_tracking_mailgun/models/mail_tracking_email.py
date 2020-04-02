# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import logging
from datetime import datetime

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split

_logger = logging.getLogger(__name__)


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

    @property
    def _mailgun_mandatory_fields(self):
        return (
            "event",
            "timestamp",
            "token",
            "signature",
            "tracking_email_id",
            "odoo_db",
        )

    @property
    def _mailgun_event_type_mapping(self):
        return {
            # Mailgun event type: tracking event type
            "delivered": "delivered",
            "opened": "open",
            "clicked": "click",
            "unsubscribed": "unsub",
            "complained": "spam",
            "bounced": "hard_bounce",
            "dropped": "reject",
            "accepted": "sent",
            "failed": "error",
            "rejected": "error",
        }

    def _mailgun_event_type_verify(self, event):
        event = event or {}
        mailgun_event_type = event.get("event")
        if mailgun_event_type not in self._mailgun_event_type_mapping:
            _logger.error("Mailgun: event type '%s' not supported", mailgun_event_type)
            return False
        # OK, event type is valid
        return True

    def _mailgun_signature(self, api_key, timestamp, token):
        return hmac.new(
            key=bytes(api_key, "utf-8"),
            msg=bytes("{}{}".format(str(timestamp), str(token)), "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

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
        return api_key, api_url, domain, validation_key

    def _mailgun_signature_verify(self, event):
        event = event or {}
        icp = self.env["ir.config_parameter"].sudo()
        api_key = icp.get_param("mailgun.apikey")
        if not api_key:
            _logger.warning(
                "No Mailgun api key configured. "
                "Please add 'mailgun.apikey' to System parameters "
                "to enable Mailgun authentication webhoook "
                "requests. More info at: "
                "https://documentation.mailgun.com/"
                "user_manual.html#webhooks"
            )
        else:
            timestamp = event.get("timestamp")
            token = event.get("token")
            signature = event.get("signature")
            event_digest = self._mailgun_signature(api_key, timestamp, token)
            if signature != event_digest:
                _logger.error(
                    "Mailgun: Invalid signature '%s' != '%s'", signature, event_digest
                )
                return False
        # OK, signature is valid
        return True

    def _db_verify(self, event):
        event = event or {}
        odoo_db = event.get("odoo_db")
        current_db = self.env.cr.dbname
        if odoo_db != current_db:
            _logger.error("Mailgun: Database '%s' is not the current database", odoo_db)
            return False
        # OK, DB is current
        return True

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
        if mailgun_event_type == "bounced":
            metadata.update(
                {
                    "error_type": event.get("code", False),
                    "error_description": event.get("error", False),
                    "error_details": event.get("notification", False),
                }
            )
        elif mailgun_event_type == "dropped":
            metadata.update(
                {
                    "error_type": event.get("reason", False),
                    "error_description": event.get("code", False),
                    "error_details": event.get("description", False),
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

    def _mailgun_tracking_get(self, event):
        tracking = False
        tracking_email_id = event.get("tracking_email_id", False)
        if tracking_email_id and tracking_email_id.isdigit():
            tracking = self.search([("id", "=", tracking_email_id)], limit=1)
        return tracking

    def _event_is_from_mailgun(self, event):
        event = event or {}
        return all([k in event for k in self._mailgun_mandatory_fields])

    @api.model
    def event_process(self, request, post, metadata, event_type=None):
        res = super(MailTrackingEmail, self).event_process(
            request, post, metadata, event_type=event_type
        )
        if res == "NONE" and self._event_is_from_mailgun(post):
            if not self._mailgun_signature_verify(post):
                res = "ERROR: Signature"
            elif not self._mailgun_event_type_verify(post):
                res = "ERROR: Event type not supported"
            elif not self._db_verify(post):
                res = "ERROR: Invalid DB"
            else:
                res = "OK"
        if res == "OK":
            mailgun_event_type = post.get("event")
            mapped_event_type = (
                self._mailgun_event_type_mapping.get(mailgun_event_type) or event_type
            )
            if not mapped_event_type:  # pragma: no cover
                res = "ERROR: Bad event"
            tracking = self._mailgun_tracking_get(post)
            if not tracking:
                res = "ERROR: Tracking not found"
        if res == "OK":
            # Complete metadata with mailgun event info
            metadata = self._mailgun_metadata(mailgun_event_type, post, metadata)
            # Create event
            tracking.event_create(mapped_event_type, metadata)
        if res != "NONE":
            if event_type:
                _logger.info("Mailgun: event '%s' process '%s'", event_type, res)
            else:
                _logger.info("Mailgun: event process '%s'", res)
        return res

    def action_manual_check_mailgun(self):
        """
        Manual check against Mailgun API
        API Documentation:
        https://documentation.mailgun.com/en/latest/api-events.html
        """
        api_key, api_url, domain, validation_key = self._mailgun_values()
        for tracking in self:
            if not tracking.mail_message_id:
                raise UserError(_("There is no tracked message!"))
            message_id = tracking.mail_message_id.message_id.replace("<", "").replace(
                ">", ""
            )
            res = requests.get(
                "{}/{}/events".format(api_url, domain),
                auth=("api", api_key),
                params={
                    "begin": tracking.timestamp,
                    "ascending": "yes",
                    "message-id": message_id,
                },
            )
            if not res or res.status_code != 200:
                raise ValidationError(_("Couldn't retrieve Mailgun information"))
            content = res.json()
            if "items" not in content:
                raise ValidationError(_("Event information not longer stored"))
            for item in content["items"]:
                # mailgun event hasn't been synced and recipient is the same as
                # in the evaluated tracking. We use email_split since tracking
                # recipient could come in format: "example" <to@dest.com>
                if not self.env["mail.tracking.event"].search(
                    [("mailgun_id", "=", item["id"])]
                ) and (item.get("recipient", "") == email_split(tracking.recipient)[0]):
                    mapped_event_type = self._mailgun_event_type_mapping.get(
                        item["event"], item["event"]
                    )
                    metadata = self._mailgun_metadata(mapped_event_type, item, {})
                    tracking.event_create(mapped_event_type, metadata)
