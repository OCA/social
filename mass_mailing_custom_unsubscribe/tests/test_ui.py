# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest import mock

from werkzeug import urls

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class UICase(HttpCase):
    def extract_url(self, mail, *args, **kwargs):
        url = mail.mailing_id._get_unsubscribe_url(self.email, mail.res_id)
        self.assertTrue(urls.url_parse(url).decode_query().get("hash_token"))
        self.assertTrue(url.startswith(self.domain))
        self.url = url.replace(self.domain, "", 1)
        return True

    def setUp(self):
        super().setUp()
        self.email = "test.contact@example.com"
        self.url = ""
        self.mail_postprocess_patch = mock.patch(
            "odoo.addons.mass_mailing.models.mail_mail.MailMail."
            "_postprocess_sent_message",
            autospec=True,
            side_effect=self.extract_url,
        )
        self.domain = self.env["ir.config_parameter"].get_param("web.base.url")
        List = self.lists = self.env["mailing.list"]
        for n in range(4):
            self.lists += List.create({"name": "test list %d" % n})
        self.contact = self.env["mailing.contact"].create(
            {
                "name": "test contact",
                "email": self.email,
                "list_ids": self.lists[:3].ids,
            }
        )
        self.mailing = self.env["mailing.mailing"].create(
            {
                "name": "test mailing %d" % n,
                "mailing_model_id": self.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(6, 0, [self.lists[0].id, self.lists[3].id])],
                "reply_to_mode": "update",
                "subject": "Test",
            }
        )
        # HACK https://github.com/odoo/odoo/pull/14429
        self.mailing.body_html = """
            <div>
                <a href="/unsubscribe_from_list">
                    This link should get the unsubscription URL
                </a>
            </div>
        """

    def tearDown(self):
        del self.email, self.lists, self.contact, self.mailing, self.url
        super().tearDown()

    def test_contact_unsubscription(self):
        """Test a mass mailing contact that wants to unsubscribe."""
        # Extract the unsubscription link from the message body
        with self.mail_postprocess_patch:
            self.mailing.action_send_mail()
        self.start_tour(
            self.url, "mass_mailing_custom_unsubscribe_tour_contact", login="admin"
        )
        # Check results from running tour
        subscription = self.contact.subscription_ids.filtered("opt_out")
        self.assertTrue("REMOTE_ADDR" in subscription.metadata)

    def test_partner_unsubscription(self):
        """Test a partner that wants to unsubscribe."""
        # Change mailing to be sent to partner
        partner_id = self.env["res.partner"].name_create(
            "Demo Partner <%s>" % self.email
        )[0]
        self.mailing.mailing_model_id = self.env.ref("base.model_res_partner")
        self.mailing.mailing_domain = repr(
            [("is_blacklisted", "=", False), ("id", "=", partner_id)]
        )
        # Extract the unsubscription link from the message body
        with self.mail_postprocess_patch:
            self.mailing.action_send_mail()
        self.start_tour(
            self.url, "mass_mailing_custom_unsubscribe_tour_partner", login="demo"
        )
        # Check results from running tour
        partner = self.env["res.partner"].browse(partner_id)
        self.assertTrue(partner.is_blacklisted)
        blacklist = self.env["mail.blacklist"].search([("email", "=", partner.email)])
        self.assertEqual(blacklist.opt_out_reason_id.name, "Other")
        self.assertTrue("REMOTE_ADDR" in "".join(blacklist.message_ids.mapped("body")))
