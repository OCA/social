# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from werkzeug import urls

from odoo.tests.common import HttpCase


class UICase(HttpCase):
    _tour_run = "odoo.__DEBUG__.services['web_tour.tour'].run('%s')"
    _tour_ready = "odoo.__DEBUG__.services['web_tour.tour'].tours.%s.ready"

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
        List = self.lists = self.env["mailing.list"]
        for n in range(4):
            self.lists += List.create({"name": "test list %d" % n})
        self.contact = self.env["mailing.contact"].create(
            {
                "name": "test contact",
                "email": self.email,
                "list_ids": [(6, False, self.lists.ids)],
            }
        )
        self.mailing = self.env["mailing.mailing"].create(
            {
                "name": "test mailing %d" % n,
                "mailing_model_id": self.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(6, 0, [self.lists[0].id, self.lists[3].id])],
                "reply_to_mode": "thread",
                "subject": "Test",
            }
        )
        self.mailing._onchange_model_and_list()
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
        super(UICase, self).tearDown()

    def test_contact_unsubscription(self):
        """Test a mass mailing contact that wants to unsubscribe."""
        # This list we are unsubscribing from, should appear always in UI
        self.lists[0].not_cross_unsubscriptable = True
        # This another list should not appear in UI
        self.lists[2].not_cross_unsubscriptable = True
        # This another list should not appear in UI, even if it is one of
        # the lists of the mailing
        self.lists[3].is_public = False
        # Extract the unsubscription link from the message body
        with self.mail_postprocess_patch:
            self.mailing.action_send_mail()

        tour = "mass_mailing_custom_unsubscribe_tour_contact"
        self.browser_js(
            url_path=self.url,
            code=self._tour_run % tour,
            ready=self._tour_ready % tour,
            login="demo",
        )

        # Check results from running tour
        self.assertFalse(self.lists[0].subscription_ids.opt_out)
        self.assertTrue(self.lists[1].subscription_ids.opt_out)
        self.assertFalse(self.lists[2].subscription_ids.opt_out)

        cnt = self.contact
        common_domain = [
            ("mass_mailing_id", "=", self.mailing.id),
            ("email", "=", self.email),
            ("unsubscriber_id", "=", "%s,%d" % (cnt._name, cnt.id)),
        ]
        # first unsubscription
        reason = "mass_mailing_custom_unsubscribe.reason_other"
        unsubscription_1 = self.env["mail.unsubscription"].search(
            common_domain
            + [
                ("action", "=", "unsubscription"),
                ("details", "=", "I want to unsubscribe because I want. " "Period."),
                ("reason_id", "=", self.env.ref(reason).id),
            ]
        )
        # second unsubscription
        reason = "mass_mailing_custom_unsubscribe.reason_not_interested"
        unsubscription_2 = self.env["mail.unsubscription"].search(
            common_domain
            + [
                ("action", "=", "unsubscription"),
                ("reason_id", "=", self.env.ref(reason).id),
            ]
        )
        # re-subscription from self.lists[3]
        unsubscription_3 = self.env["mail.unsubscription"].search(
            common_domain + [("action", "=", "subscription")]
        )
        # unsubscriptions above are all unsubscriptions saved during the
        # tour and they are all the existing unsubscriptions
        self.assertEqual(
            unsubscription_1 | unsubscription_2 | unsubscription_3,
            self.env["mail.unsubscription"].search([]),
        )
        self.assertEqual(3, len(self.env["mail.unsubscription"].search([])))

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

        tour = "mass_mailing_custom_unsubscribe_tour_partner"
        self.browser_js(
            url_path=self.url,
            code=self._tour_run % tour,
            ready=self._tour_ready % tour,
            login="demo",
        )

        # Check results from running tour
        partner = self.env["res.partner"].browse(partner_id)
        self.assertTrue(partner.is_blacklisted)
        reason_xid = "mass_mailing_custom_unsubscribe.reason_not_interested"
        unsubscriptions = self.env["mail.unsubscription"].search(
            [
                ("action", "=", "blacklist_add"),
                ("mass_mailing_id", "=", self.mailing.id),
                ("email", "=", self.email),
                ("unsubscriber_id", "=", "res.partner,%d" % partner_id),
                ("details", "=", False),
                ("reason_id", "=", self.env.ref(reason_xid).id),
            ]
        )
        self.assertEqual(1, len(unsubscriptions))
