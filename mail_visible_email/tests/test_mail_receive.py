# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.test_mail.data.test_mail_data import MAIL_TEMPLATE


@tagged("-at_install", "post_install")
class TestMailReceive(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Alias = cls.env["mail.alias"]
        cls.Partner = cls.env["res.partner"]
        cls.MailThread = cls.env["mail.thread"]
        cls.Message = cls.env["mail.message"]
        cls.alias_domain = cls.env["mail.alias.domain"].create(
            {
                "name": "fsf.org",
                "catchall_alias": "catchall",
            }
        )
        cls.env.company.alias_domain_id = cls.alias_domain

        cls.partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")])
        cls.mail_alias_test = cls.Alias.create(
            {
                "alias_name": "test_alias",
                "alias_domain_id": cls.alias_domain.id,
                "alias_model_id": cls.partner_model.id,
                "alias_defaults": "{'name': 'Test Alias', 'is_company': True}",
            }
        )

    @mute_logger("odoo.addons.mail.models.mail_thread", "odoo.models")
    def test_incoming_email(self):
        # Imitate what self.server.fetch_mail() would do
        thread_id = self.MailThread.message_process(
            self.Partner._name,
            MAIL_TEMPLATE.format(
                return_path="spambot@example.com",
                email_from="spambot@example.com",
                to="test_alias@fsf.org",
                cc="nobody@fsf.org, anybody@fsf.org",
                subject="I'm a robot, hello",
                extra="",
                msg_id="<fitter.happier.more.productive@example.com>",
            ),
        )
        self.assertTrue(thread_id)
        partner = self.Partner.browse(thread_id)
        self.assertEqual(partner.name, "Test Alias")
        message = self.Message.search(
            [
                ("model", "=", partner._name),
                ("res_id", "=", partner.id),
            ]
        )
        self.assertTrue(message)
        self.assertEqual(message.email_to, "test_alias@fsf.org")
        self.assertIn("anybody@fsf.org", message.email_cc)
        self.assertIn("nobody@fsf.org", message.email_cc)
