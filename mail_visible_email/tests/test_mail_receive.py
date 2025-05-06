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

        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("mail.catchall.domain", "fsf.org")

        cls.partner_model = cls.env["ir.model"].search([("model", "=", "res.partner")])
        cls.mail_alias_test = cls.Alias.create(
            {
                "alias_name": "test_alias",
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
        # We should now have a partner with the name 'Test Alias'.
        self.assertTrue(thread_id)
        partner = self.Partner.browse(thread_id)
        self.assertEqual(partner.name, "Test Alias")
        # We should have a mail message referring to this partner.
        message = self.Message.search(
            [
                ("model", "=", partner._name),
                ("res_id", "=", partner.id),
            ]
        )
        self.assertTrue(message)
        self.assertEqual(message.email_to, "test_alias@fsf.org")
        # Use In to be independent of ordering and separator.
        self.assertIn("anybody@fsf.org", message.email_cc)
        self.assertIn("nobody@fsf.org", message.email_cc)
