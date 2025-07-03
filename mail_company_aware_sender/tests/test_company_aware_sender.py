# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import Command
from odoo.tests import TransactionCase


class TestCompanyAwareSender(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create two companies and a partner/user.
        cls.Company = cls.env["res.company"]
        cls.Partner = cls.env["res.partner"]
        cls.User = cls.env["res.users"]
        cls.IrMailServer = cls.env["ir.mail_server"]
        cls.mail_server = cls.IrMailServer.create(
            {
                "name": "localhost",
                "smtp_host": "localhost",
                "domain_whitelist": "therp.nl",
            }
        )
        cls.company_kingdom = cls.Company.create(
            {
                "name": "The kingdom of France",
                "email": "info@kingdom.fr",
            }
        )
        cls.company_imperium = cls.Company.create(
            {
                "name": "Imperium Romanum",
                "email": "chancellery@imperiumromanum.org",
                "use_email_domain": True,
                "format_email": False,
            }
        )
        cls.partner_charles = cls.Partner.create(
            {
                "name": "Charles Le Magne",
                "email": "charlemagne@therp.nl",
            }
        )
        cls.user_charles = cls.User.with_context(no_reset_password=True).create(
            {
                "partner_id": cls.partner_charles.id,
                "login": "charlemagne",
                "email": "charlemagne@therp.nl",
                "company_id": cls.company_kingdom.id,
                "company_ids": [
                    Command.set([cls.company_kingdom.id, cls.company_imperium.id]),
                ],
            }
        )

    def test_nothing_changed(self):
        # Check with default user and author (current user).
        mail_thread = (
            self.env["mail.thread"]
            .with_user(self.user_charles)
            .with_company(self.company_kingdom)
        )
        author_id, email_from = mail_thread._message_compute_author(None, None)
        self.assertEqual(author_id, self.partner_charles.id)
        self.assertEqual(email_from, '"Charles Le Magne" <charlemagne@therp.nl>')
        author_id, email_from = mail_thread._message_compute_author(
            None, '"Unknown Person" <unknown.person@example.com>'
        )
        self.assertEqual(author_id, False)
        self.assertEqual(email_from, '"Unknown Person" <unknown.person@example.com>')

    def test_company_overwrite(self):
        # Check with default user and author (current user).
        mail_thread = (
            self.env["mail.thread"]
            .with_user(self.user_charles)
            .with_company(self.company_imperium)
        )
        # Should not work if domain not whitelisted.
        author_id, email_from = mail_thread._message_compute_author(None, None)
        self.assertEqual(author_id, self.partner_charles.id)
        self.assertEqual(email_from, '"Charles Le Magne" <charlemagne@therp.nl>')
        # Whitelist domain.
        self.mail_server.write(
            {"domain_whitelist": "therp.nl,kingdom.fr,imperiumromanum.org"}
        )
        author_id, email_from = mail_thread._message_compute_author(None, None)
        self.assertEqual(author_id, self.partner_charles.id)
        self.assertEqual(email_from, "charlemagne@imperiumromanum.org")
        self.company_imperium.write({"format_email": True})
        author_id, email_from = mail_thread._message_compute_author(None, None)
        self.assertEqual(author_id, self.partner_charles.id)
        self.assertEqual(
            email_from, '"Charles Le Magne" <charlemagne@imperiumromanum.org>'
        )
