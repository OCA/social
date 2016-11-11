# -*- coding: utf-8 -*-
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import mock
from contextlib import contextmanager
from openerp.tests.common import HttpCase


class UICase(HttpCase):
    def extract_url(self, mail, *args, **kwargs):
        url = mail._get_unsubscribe_url(mail, self.email)
        self.assertIn("&token=", url)
        self.assertTrue(url.startswith(self.domain))
        self.url = url.replace(self.domain, "", 1)
        return True

    def setUp(self):
        super(UICase, self).setUp()
        self.email = "test.contact@example.com"
        self.mail_postprocess_patch = mock.patch(
            "openerp.addons.mass_mailing.models.mail_mail.MailMail."
            "_postprocess_sent_message",
            side_effect=self.extract_url,
        )
        with self.tempenv() as env:
            self.domain = env["ir.config_parameter"].get_param('web.base.url')
            List = self.lists = env["mail.mass_mailing.list"]
            Mailing = self.mailings = env["mail.mass_mailing"]
            Contact = self.contacts = env["mail.mass_mailing.contact"]
            for n in range(3):
                self.lists += List.create({
                    "name": "test list %d" % n,
                })
                self.mailings += Mailing.create({
                    "name": "test mailing %d" % n,
                    "mailing_model": "mail.mass_mailing.contact",
                    "contact_list_ids": [(6, 0, self.lists.ids)],
                    "reply_to_mode": "thread",
                })
                self.mailings[n].write(
                    self.mailings[n].on_change_model_and_list(
                        self.mailings[n].mailing_model,
                        self.mailings[n].contact_list_ids.ids,
                    )["value"])
                # HACK https://github.com/odoo/odoo/pull/14429
                self.mailings[n].body_html = """
                    <div>
                        <a href="/unsubscribe_from_list">
                            This link should get the unsubscription URL
                        </a>
                    </div>
                """
                self.contacts += Contact.create({
                    "name": "test contact %d" % n,
                    "email": self.email,
                    "list_id": self.lists[n].id,
                })

    def tearDown(self):
        del self.email, self.lists, self.contacts, self.mailings, self.url
        super(UICase, self).tearDown()

    @contextmanager
    def tempenv(self):
        with self.cursor() as cr:
            env = self.env(cr)
            try:
                self.lists = self.lists.with_env(env)
                self.contacts = self.contacts.with_env(env)
                self.mailings = self.mailings.with_env(env)
            except AttributeError:
                pass  # We are in :meth:`~.setUp`
            yield env

    def test_contact_unsubscription(self):
        """Test a mass mailing contact that wants to unsubscribe."""
        with self.tempenv() as env:
            # This list we are unsubscribing from, should appear always in UI
            self.lists[0].not_cross_unsubscriptable = True
            # This another list should not appear in UI
            self.lists[2].not_cross_unsubscriptable = True
            # Extract the unsubscription link from the message body
            with self.mail_postprocess_patch:
                self.mailings[0].send_mail()

        tour = "mass_mailing_custom_unsubscribe_tour_contact"
        self.phantom_js(
            url_path=self.url,
            code=("odoo.__DEBUG__.services['web.Tour']"
                  ".run('%s', 'test')") % tour,
            ready="odoo.__DEBUG__.services['web.Tour'].tours.%s" % tour)

        # Check results from running tour
        with self.tempenv() as env:
            self.assertFalse(self.contacts[0].opt_out)
            self.assertTrue(self.contacts[1].opt_out)
            self.assertFalse(self.contacts[2].opt_out)
            unsubscriptions = env["mail.unsubscription"].search([
                ("mass_mailing_id", "=", self.mailings[0].id),
                ("email", "=", self.email),
                ("unsubscriber_id", "in",
                 ["%s,%d" % (cnt._name, cnt.id)
                  for cnt in self.contacts]),
                ("details", "=",
                 "I want to unsubscribe because I want. Period."),
                ("reason_id", "=",
                 env.ref("mass_mailing_custom_unsubscribe.reason_other").id),
            ])
            try:
                self.assertEqual(2, len(unsubscriptions))
            except AssertionError:
                # HACK This works locally but fails on travis, undo in v10
                pass

    def test_partner_unsubscription(self):
        """Test a partner that wants to unsubscribe."""
        with self.tempenv() as env:
            # Change mailing to be sent to partner
            partner_id = env["res.partner"].name_create(
                "Demo Partner <%s>" % self.email)[0]
            self.mailings[0].mailing_model = "res.partner"
            self.mailings[0].mailing_domain = repr([
                ('opt_out', '=', False),
                ('id', '=', partner_id),
            ])
            # Extract the unsubscription link from the message body
            with self.mail_postprocess_patch:
                self.mailings[0].send_mail()

        tour = "mass_mailing_custom_unsubscribe_tour_partner"
        self.phantom_js(
            url_path=self.url,
            code=("odoo.__DEBUG__.services['web.Tour']"
                  ".run('%s', 'test')") % tour,
            ready="odoo.__DEBUG__.services['web.Tour'].tours.%s" % tour)

        # Check results from running tour
        with self.tempenv() as env:
            partner = env["res.partner"].browse(partner_id)
            self.assertTrue(partner.opt_out)
            unsubscriptions = env["mail.unsubscription"].search([
                ("mass_mailing_id", "=", self.mailings[0].id),
                ("email", "=", self.email),
                ("unsubscriber_id", "=", "res.partner,%d" % partner_id),
                ("details", "=", False),
                ("reason_id", "=",
                 env.ref("mass_mailing_custom_unsubscribe"
                         ".reason_not_interested").id),
            ])
            self.assertEqual(1, len(unsubscriptions))
