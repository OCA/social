# Copyright 2016 Tecnativa - Antonio Espinosa
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from contextlib import contextmanager, suppress

import mock
from freezegun import freeze_time
from werkzeug.exceptions import NotAcceptable

from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.tests.common import Form, TransactionCase
from odoo.tools import mute_logger

from ..controllers.main import MailTrackingController

# HACK https://github.com/odoo/odoo/pull/78424 because website is not dependency
try:
    from odoo.addons.website.tools import MockRequest
except ImportError:
    MockRequest = None


_packagepath = "odoo.addons.mail_tracking_mailgun"


@freeze_time("2016-08-12 17:00:00", tick=True)
class TestMailgun(TransactionCase):
    def mail_send(self):
        mail = self.env["mail.mail"].create(
            {
                "subject": "Test subject",
                "email_from": "from@example.com",
                "email_to": self.recipient,
                "body_html": "<p>This is a test message</p>",
                "message_id": "<test-id@f187c54734e8>",
            }
        )
        mail.send()
        # Search tracking created
        tracking_email = self.env["mail.tracking.email"].search(
            [("mail_id", "=", mail.id)]
        )
        return mail, tracking_email

    def setUp(self):
        super().setUp()
        self.recipient = "to@example.com"
        self.mail, self.tracking_email = self.mail_send()
        self.domain = "example.com"
        # Configure Mailgun through GUI
        cf = Form(self.env["res.config.settings"])
        cf.mail_tracking_mailgun_enabled = True
        cf.mail_tracking_mailgun_api_key = (
            cf.mail_tracking_mailgun_webhook_signing_key
        ) = (
            cf.mail_tracking_mailgun_validation_key
        ) = "key-12345678901234567890123456789012"
        cf.mail_tracking_mailgun_domain = False
        cf.mail_tracking_mailgun_auto_check_partner_emails = False
        config = cf.save()
        # Done this way as `hr_expense` adds this field again as readonly, and thus Form
        # doesn't process it correctly
        config.alias_domain = self.domain
        config.execute()
        self.token = "f1349299097a51b9a7d886fcb5c2735b426ba200ada6e9e149"
        self.timestamp = "1471021089"
        self.signature = (
            "4fb6d4dbbe10ce5d620265dcd7a3c0b8" "ca0dede1433103891bc1ae4086e9d5b2"
        )
        self.event = {
            "log-level": "info",
            "id": "oXAVv5URCF-dKv8c6Sa7T",
            "timestamp": 1471021089.0,
            "message": {
                "headers": {
                    "to": "test@test.com",
                    "message-id": "test-id@f187c54734e8",
                    "from": "Mr. Odoo <mrodoo@odoo.com>",
                    "subject": "This is a test",
                },
            },
            "event": "delivered",
            "recipient": "to@example.com",
            "user-variables": {
                "odoo_db": self.env.cr.dbname,
                "tracking_email_id": self.tracking_email.id,
            },
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
        self.response = {"items": [self.event]}
        self.MailTrackingController = MailTrackingController()

    @contextmanager
    def _request_mock(self, reset_replay_cache=True):
        # HACK https://github.com/odoo/odoo/pull/78424
        if MockRequest is None:
            self.skipTest("MockRequest not found, sorry")
        if reset_replay_cache:
            with suppress(AttributeError):
                del self.env.registry._mail_tracking_mailgun_processed_tokens
        # Imitate Mailgun JSON request
        mock = MockRequest(self.env)
        with mock as request:
            request.jsonrequest = {
                "signature": {
                    "timestamp": self.timestamp,
                    "token": self.token,
                    "signature": self.signature,
                },
                "event-data": self.event,
            }
            request.params = {"db": self.env.cr.dbname}
            request.session.db = self.env.cr.dbname
            yield request

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
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._mailgun_values()

    def test_no_domain(self):
        self.env["ir.config_parameter"].set_param("mail.catchall.domain", "")
        with self.assertRaises(ValidationError):
            self.env["mail.tracking.email"]._mailgun_values()
        # now we set an specific domain for Mailgun:
        # i.e: we configure new EU zone without loosing old domain statistics
        self.env["ir.config_parameter"].set_param("mailgun.domain", "eu.example.com")
        self.test_event_delivered()

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_bad_signature(self):
        self.signature = "bad_signature"
        with self._request_mock(), self.assertRaises(NotAcceptable):
            self.MailTrackingController.mail_tracking_mailgun_webhook()

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_bad_event_type(self):
        old_events = self.tracking_email.tracking_event_ids
        self.event.update({"event": "bad_event"})
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        self.assertFalse(self.tracking_email.tracking_event_ids - old_events)

    def test_bad_ts(self):
        self.timestamp = "7a"  # Now time will be used instead
        self.signature = (
            "06cc05680f6e8110e59b41152b2d1c0f1045d755ef2880ff922344325c89a6d4"
        )
        with self._request_mock(), self.assertRaises(ValueError):
            self.MailTrackingController.mail_tracking_mailgun_webhook()

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_tracking_not_found(self):
        self.event.update(
            {
                "event": "delivered",
                "message": {
                    "headers": {
                        "to": "else@test.com",
                        "message-id": "test-id-else@f187c54734e8",
                        "from": "Mr. Odoo <mrodoo@odoo.com>",
                        "subject": "This is a bad test",
                    },
                },
                "user-variables": {
                    "odoo_db": self.env.cr.dbname,
                    "tracking_email_id": -1,
                },
            }
        )
        with self._request_mock(), self.assertRaises(MissingError):
            self.MailTrackingController.mail_tracking_mailgun_webhook()

    @mute_logger("odoo.addons.mail_tracking_mailgun.models.mail_tracking_email")
    def test_tracking_wrong_db(self):
        self.event["user-variables"]["odoo_db"] = "%s_nope" % self.env.cr.dbname
        with self._request_mock(), self.assertRaises(ValidationError):
            self.MailTrackingController.mail_tracking_mailgun_webhook()

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-deliveries
    def test_event_delivered(self):
        self.event.update({"event": "delivered"})
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        events = self.event_search("delivered")
        for event in events:
            self.assertEqual(event.timestamp, float(self.timestamp))
            self.assertEqual(event.recipient, self.recipient)

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-opens
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
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
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

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-clicks
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
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
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

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-unsubscribes
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
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        event = self.event_search("unsub")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.ip, ip)
        self.assertEqual(event.user_agent, user_agent)
        self.assertEqual(event.os_family, os_family)
        self.assertEqual(event.ua_family, ua_family)
        self.assertEqual(event.ua_type, ua_type)
        self.assertEqual(event.mobile, True)

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-spam-complaints
    def test_event_complained(self):
        self.event.update({"event": "complained"})
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        event = self.event_search("spam")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, "spam")

    # https://documentation.mailgun.com/en/latest/user_manual.html#tracking-bounces
    def test_event_failed(self):
        code = 550
        error = (
            "5.1.1 The email account does not exist.\n"
            "5.1.1 double-checking the recipient's email address"
        )
        notification = "Please, check recipient's email address"
        self.event.update(
            {
                "event": "failed",
                "delivery-status": {
                    "attempt-no": 1,
                    "code": code,
                    "description": notification,
                    "message": error,
                    "session-seconds": 0.0,
                },
                "severity": "permanent",
            }
        )
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        event = self.event_search("hard_bounce")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, str(code))
        self.assertEqual(event.error_description, error)
        self.assertEqual(event.error_details, notification)

    def test_event_rejected(self):
        reason = "hardfail"
        description = "Not delivering to previously bounced address"
        self.event.update(
            {
                "event": "rejected",
                "reject": {"reason": reason, "description": description},
            }
        )
        with self._request_mock():
            self.MailTrackingController.mail_tracking_mailgun_webhook()
        event = self.event_search("reject")
        self.assertEqual(event.timestamp, float(self.timestamp))
        self.assertEqual(event.recipient, self.recipient)
        self.assertEqual(event.error_type, "rejected")
        self.assertEqual(event.error_description, reason)
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
        # If we autocheck, the mail will be bounced
        self.partner.with_context(mailgun_auto_check=True).check_email_validity()
        self.assertTrue(self.partner.email_bounced)
        # Unable to fully validate
        mock_request.get.return_value.json.return_value = {
            "is_valid": True,
            "mailbox_verification": "unknown",
        }
        with self.assertRaises(UserError):
            self.partner.check_email_validity()

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
        self.assertTrue(event)
        self.assertEqual(event.event_type, self.response["items"][0]["event"])

    @mock.patch(_packagepath + ".models.mail_tracking_email.requests")
    def test_manual_check_exceptions(self, mock_request):
        mock_request.get.return_value.status_code = 404
        with self.assertRaises(UserError):
            self.tracking_email.action_manual_check_mailgun()
        mock_request.get.return_value.status_code = 200
        mock_request.get.return_value.json.return_value = {}
        with self.assertRaises(UserError):
            self.tracking_email.action_manual_check_mailgun()
