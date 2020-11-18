# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from werkzeug import urls

from odoo.tests.common import HttpCase


class UICase(HttpCase):
    def extract_url(self, mail, *args, **kwargs):
        url = mail._get_unsubscribe_url(self.email)
        self.assertTrue(urls.url_parse(url).decode_query().get("token"))
        self.assertTrue(url.startswith(self.domain))
        self.url = url.replace(self.domain, "", 1)
        return True

    def setUp(self):
        super(UICase, self).setUp()
        self.email = "test.contact@example.com"
        self.mail_postprocess_patch = mock.patch(
            "odoo.addons.mass_mailing.models.mail_mail.MailMail."
            "_postprocess_sent_message",
            autospec=True,
            side_effect=self.extract_url,
        )

        self.domain = self.env["ir.config_parameter"].get_param("web.base.url")

        self.partner = self.env["res.partner"].create(
            {"name": "Demo Partner <%s>" % self.email, "email": self.email}
        )

        self.event_1 = self.env["event.event"].create(
            {
                "name": "test_event_2",
                "event_type_id": 1,
                "date_end": "2012-01-01 19:05:15",
                "date_begin": "2012-01-01 18:05:15",
            }
        )
        self.event_2 = self.env["event.event"].create(
            {
                "name": "test_event_2",
                "event_type_id": 1,
                "date_end": "2012-01-01 19:05:15",
                "date_begin": "2012-01-01 18:05:15",
            }
        )
        self.event_registration_1 = self.env["event.registration"].create(
            {
                "name": "test_registration_1",
                "event_id": self.event_1.id,
                "email": self.email,
                "partner_id": self.partner.id,
            }
        )
        self.event_registration_2 = self.env["event.registration"].create(
            {
                "name": "test_registration_2",
                "event_id": self.event_2.id,
                "email": self.email,
                "partner_id": self.partner.id,
            }
        )

        self.mailing_1 = self.env["mailing.mailing"].create(
            {
                "name": "test_mailing_1",
                "mailing_model_id": self.env.ref("event.model_event_registration").id,
                "mailing_domain": "[['id','=',%s]]" % self.event_registration_1.id,
                "reply_to_mode": "email",
                "subject": "Test 1",
            }
        )
        self.mailing_1._onchange_model_and_list()
        # HACK https://github.com/odoo/odoo/pull/14429
        self.mailing_1.body_html = """
            <div>
                <a href="/unsubscribe_from_list">
                    This link should get the unsubscription URL
                </a>
            </div>
        """

        self.mailing_2 = self.env["mailing.mailing"].create(
            {
                "name": "test_mailing_2",
                "mailing_model_id": self.env.ref("event.model_event_registration").id,
                "mailing_domain": "[['id','=',%s]]" % self.event_registration_2.id,
                "reply_to_mode": "email",
                "subject": "Test 2",
            }
        )
        self.mailing_2._onchange_model_and_list()
        # HACK https://github.com/odoo/odoo/pull/14429
        self.mailing_2.body_html = """
            <div>
                <a href="/unsubscribe_from_list">
                    This link should get the unsubscription URL
                </a>
            </div>
        """

    def tearDown(self):
        del (
            self.email,
            self.event_1,
            self.event_2,
            self.event_registration_1,
            self.event_registration_2,
            self.mailing_1,
            self.mailing_2,
            self.partner,
            self.url,
        )
        super(UICase, self).tearDown()

    def test_unsubscription_event_1(self):
        """Test a mass mailing contact that wants to unsubscribe."""
        # Extract the unsubscription link from the message body
        with self.mail_postprocess_patch:
            self.mailing_1.action_send_mail()

        tour = "mass_mailing_custom_unsubscribe_event_tour"
        self.start_tour(url_path=self.url, tour_name=tour, login="demo")

        # Check results from running tour
        # User should be opted out from event 1 mailing list
        self.assertTrue(self.event_registration_1.opt_out)
        # User should not be opted out from event 2 mailing list
        self.assertFalse(self.event_registration_2.opt_out)

        reason_xid = "mass_mailing_custom_unsubscribe.reason_not_interested"
        unsubscriptions = self.env["mail.unsubscription"].search(
            [
                ("action", "=", "unsubscription"),
                ("mass_mailing_id", "=", self.mailing_1.id),
                ("email", "=", self.email),
                (
                    "unsubscriber_id",
                    "=",
                    "event.registration,%d" % self.event_registration_1.id,
                ),
                ("details", "=", False),
                ("reason_id", "=", self.env.ref(reason_xid).id),
            ]
        )
        # Unsubscription record must exist
        self.assertEqual(1, len(unsubscriptions))

        self.mailing_2.action_send_mail()

        # Mail to user must have been sent
        self.assertEqual(1, self.mailing_2.sent)
