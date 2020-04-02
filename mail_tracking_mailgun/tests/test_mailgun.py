# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

_packagepath = "odoo.addons.mail_tracking_mailgun"


class TestMailgun(TransactionCase):
    def mail_send(self):
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "email_from": "from@example.com",
                "email_to": self.recipient,
                "body_html": "<p>This is a test message</p>",
            }
        )
        mail.send()
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [("mail_id", "=", mail.id)]
        )
        return mail, tracking_email

    def setUp(self):
        super(TestMailgun, self).setUp()
        self.recipient = "to@example.com"
        self.mail, self.tracking_email = self.mail_send()
        self.api_key = "key-12345678901234567890123456789012"
        self.domain = "example.com"
        self.token = "f1349299097a51b9a7d886fcb5c2735b426ba200ada6e9e149"
        self.timestamp = "1471021089"
        self.signature = (
            "4fb6d4dbbe10ce5d620265dcd7a3c0b8ca0dede1433103891bc1ae4086e9d5b2"
        )
        self.env["ir.config_parameter"].set_param("mailgun.apikey", self.api_key)
        self.env["ir.config_parameter"].set_param("mail.catchall.domain", self.domain)
        self.env["ir.config_parameter"].set_param(
            "mailgun.validation_key", self.api_key
        )
        self.env["ir.config_parameter"].set_param(
            "mailgun.auto_check_partner_email", ""
        )
        self.event = {
            "Message-Id": "<xxx.xxx.xxx-openerp-xxx-res.partner@test_db>",
            "X-Mailgun-Sid": "WyIwNjgxZSIsICJ0b0BleGFtcGxlLmNvbSIsICI3MGI0MWYiXQ==",
            "token": self.token,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "domain": "example.com",
            "message-headers": "[]",
            "recipient": self.recipient,
            "odoo_db": self.env.cr.dbname,
            "tracking_email_id": "%s" % self.tracking_email.id,
        }
        self.metadata = {
            "ip": "127.0.0.1",
            "user_agent": False,
            "os_family": False,
            "ua_family": False,
        }
        self.partner = self.env["res.partner"].create(
            {"name": "Mr. Odoo", "email": "mrodoo@example.com"}
        )
        self.response = {
            "items": [
                {
                    "log-level": "info",
                    "id": "oXAVv5URCF-dKv8c6Sa7T",
                    "timestamp": 1509119329.0,
                    "message": {
                        "headers": {
                            "to": "test@test.com",
                            "message-id": "test-id@f187c54734e8",
                            "from": "Mr. Odoo <mrodoo@odoo.com>",
                            "subject": "This is a test",
                        }
                    },
                    "event": "delivered",
                    "recipient": "to@example.com",
                }
            ]
        }

    def event_search(self, event_type):
        event = self.env["mail.tracking.event"].search(
            [
                ("tracking_email_id", "=", self.tracking_email.id),
                ("event_type", "=", event_type),
            ]
        )
        self.assertTrue(event)
        return event

    def test_no_api_key(self):
        self.env["ir.config_parameter"].set_param("mailgun.apikey", "")
        self.test_event_delivered()
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._mailgun_values()

    def test_no_domain(self):
        self.env["ir.config_parameter"].set_param("mail.catchall.domain", "")
        self.test_event_delivered()
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._mailgun_values()
        # now we set an specific domain for Mailgun:
        # i.e: we configure new EU zone without loosing old domain statistics
        self.env["ir.config_parameter"].set_param("mailgun.domain", "eu.example.com")
        self.test_event_delivered()

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_bad_signature(self):
        self.event.update({"event": "delivered", "signature": "bad_signature"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("ERROR: Signature", response)

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_bad_event_type(self):
        self.event.update({"event": "bad_event"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("ERROR: Event type not supported", response)

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_bad_db(self):
        self.event.update({"event": "delivered", "odoo_db": "bad_db"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("ERROR: Invalid DB", response)

    def test_bad_ts(self):
        timestamp = "7a"  # Now time will be used instead
        signature = "06cc05680f6e8110e59b41152b2d1c0f1045d755ef2880ff922344325c89a6d4"
        self.event.update(
            {"event": "delivered", "timestamp": timestamp, "signature": signature}
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_tracking_not_found(self):
        self.event.update({"event": "delivered", "tracking_email_id": "bad_id"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("ERROR: Tracking not found", response)

    # https://documentation.mailgun.com/user_manual.html#tracking-deliveries
    def test_event_delivered(self):
        self.event.update({"event": "delivered"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        events = self.event_search("delivered")
        for event in events:
            self.assertEqual(event.timestamp, float(self.timestamp))
            self.assertEqual(event.recipient, self.recipient)

    # https://documentation.mailgun.com/user_manual.html#tracking-opens
    def test_event_opened(self):
        ip = "127.0.0.1"
        user_agent = "Odoo Test/8.0 Gecko Firefox/11.0"
        os_family = "Linux"
        ua_family = "Firefox"
        ua_type = "browser"
        self.event.update(
            {
                "event": "opened",
                "city": "Mountain View",
                "country": "US",
                "region": "CA",
                "client-name": ua_family,
                "client-os": os_family,
                "client-type": ua_type,
                "device-type": "desktop",
                "ip": ip,
                "user-agent": user_agent,
            }
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        event = self.event_search("open")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, False)
        self.assertEqual(event.user_country_id.code, "US")

    # https://documentation.mailgun.com/user_manual.html#tracking-clicks
    def test_event_clicked(self):
        ip = "127.0.0.1"
        user_agent = "Odoo Test/8.0 Gecko Firefox/11.0"
        os_family = "Linux"
        ua_family = "Firefox"
        ua_type = "browser"
        url = "https://odoo-community.org"
        self.event.update(
            {
                "event": "clicked",
                "city": "Mountain View",
                "country": "US",
                "region": "CA",
                "client-name": ua_family,
                "client-os": os_family,
                "client-type": ua_type,
                "device-type": "tablet",
                "ip": ip,
                "user-agent": user_agent,
                "url": url,
            }
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata, event_type="click"
        )
        self.assertEqual("OK", response)
        event = self.event_search("click")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, True)
        self.assertEqual(event.url, url)

    # https://documentation.mailgun.com/user_manual.html#tracking-unsubscribes
    def test_event_unsubscribed(self):
        ip = "127.0.0.1"
        user_agent = "Odoo Test/8.0 Gecko Firefox/11.0"
        os_family = "Linux"
        ua_family = "Firefox"
        ua_type = "browser"
        self.event.update(
            {
                "event": "unsubscribed",
                "city": "Mountain View",
                "country": "US",
                "region": "CA",
                "client-name": ua_family,
                "client-os": os_family,
                "client-type": ua_type,
                "device-type": "mobile",
                "ip": ip,
                "user-agent": user_agent,
            }
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        event = self.event_search("unsub")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, True)

    # https://documentation.mailgun.com/
    #   user_manual.html#tracking-spam-complaints
    def test_event_complained(self):
        self.event.update({"event": "complained"})
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        event = self.event_search("spam")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, "spam")

    # https://documentation.mailgun.com/user_manual.html#tracking-bounces
    def test_event_bounced(self):
        code = "550"
        error = (
            "5.1.1 The email account does not exist.\n"
            "5.1.1 double-checking the recipient's email address"
        )
        notification = "Please, check recipient's email address"
        self.event.update(
            {
                "event": "bounced",
                "code": code,
                "error": error,
                "notification": notification,
            }
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        event = self.event_search("hard_bounce")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, code)
        self.assertEqual(event.error_description, error)
        self.assertEqual(event.error_details, notification)

    # https://documentation.mailgun.com/user_manual.html#tracking-failures
    def test_event_dropped(self):
        reason = "hardfail"
        code = "605"
        description = "Not delivering to previously bounced address"
        self.event.update(
            {
                "event": "dropped",
                "reason": reason,
                "code": code,
                "description": description,
            }
        )
        response = self.env["mail.tracking.email"].event_process(
            None, self.event, self.metadata
        )
        self.assertEqual("OK", response)
        event = self.event_search("reject")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, reason)
        self.assertEqual(event.error_description, code)
        self.assertEqual(event.error_details, description)

    @mock.patch(_packagepath + ".models.res_partner.requests")
    def test_email_validity(self, mock_request):
        self.partner.email_bounced = False
        mock_request.get.return_value.apparent_encoding = "ascii"
        mock_request.get.return_value.status_code = 200
        mock_request.get.return_value.json.return_value = {
            "is_valid": True,
            "mailbox_verification": "true",
        }
        # Trigger email auto validation in partner
        self.env["ir.config_parameter"].set_param(
            "mailgun.auto_check_partner_email", "True"
        )
        self.partner.email = "info@tecnativa.com"
        self.assertFalse(self.partner.email_bounced)
        self.partner.email = "xoxoxoxo@tecnativa.com"
        # Not a valid mailbox
        mock_request.get.return_value.json.return_value = {
            "is_valid": True,
            "mailbox_verification": "false",
        }
        with self.assertRaises(UserError):
            self.partner.check_email_validity()
        # Not a valid mail address
        mock_request.get.return_value.json.return_value = {
            "is_valid": False,
            "mailbox_verification": "false",
        }
        with self.assertRaises(UserError):
            self.partner.check_email_validity()
        # Unable to fully validate
        mock_request.get.return_value.json.return_value = {
            "is_valid": True,
            "mailbox_verification": "unknown",
        }
        with self.assertRaises(UserError):
            self.partner.check_email_validity()
        self.assertTrue(self.partner.email_bounced)

    @mock.patch(_packagepath + ".models.res_partner.requests")
    def test_email_validity_exceptions(self, mock_request):
        mock_request.get.return_value.status_code = 404
        with self.assertRaises(UserError):
            self.partner.check_email_validity()
        self.env["ir.config_parameter"].set_param("mailgun.validation_key", "")
        with self.assertRaises(UserError):
            self.partner.check_email_validity()

    @mock.patch(_packagepath + ".models.res_partner.requests")
    def test_bounced(self, mock_request):
        self.partner.email_bounced = True
        mock_request.get.return_value.status_code = 404
        self.partner.check_email_bounced()
        self.assertFalse(self.partner.email_bounced)
        mock_request.get.return_value.status_code = 200
        self.partner.force_set_bounced()
        self.partner.check_email_bounced()
        self.assertTrue(self.partner.email_bounced)
        mock_request.delete.return_value.status_code = 200
        self.partner.force_unset_bounced()
        self.assertFalse(self.partner.email_bounced)

    def test_email_bounced_set(self):
        message_number = len(self.partner.message_ids) + 1
        self.partner._email_bounced_set("test_error", False)
        self.assertEqual(len(self.partner.message_ids), message_number)
        self.partner.email = ""
        self.partner._email_bounced_set("test_error", False)
        self.assertEqual(len(self.partner.message_ids), message_number)

    @mock.patch(_packagepath + ".models.mail_tracking_email.requests")
    def test_manual_check(self, mock_request):
        mock_request.get.return_value.json.return_value = self.response
        mock_request.get.return_value.status_code = 200
        self.tracking_email.action_manual_check_mailgun()
        event = self.env["mail.tracking.event"].search(
            [("mailgun_id", "=", self.response["items"][0]["id"])]
        )
        self.assertEqual(event.event_type, self.response["items"][0]["event"])

    @mock.patch(_packagepath + ".models.mail_tracking_email.requests")
    def test_manual_check_exceptions(self, mock_request):
        mock_request.get.return_value.status_code = 404
        with self.assertRaises(ValidationError):
            self.tracking_email.action_manual_check_mailgun()
        mock_request.get.return_value.status_code = 200
        mock_request.get.return_value.json.return_value = {}
        with self.assertRaises(ValidationError):
            self.tracking_email.action_manual_check_mailgun()
