# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from .common import CompanyAwareSenderCase


class TestCompanyAwareSender(CompanyAwareSenderCase):
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
        # Now opt out for the override.
        self.partner_charles.write({"fixed_email": True})
        author_id, email_from = mail_thread._message_compute_author(None, None)
        self.assertEqual(author_id, self.partner_charles.id)
        self.assertEqual(email_from, '"Charles Le Magne" <charlemagne@therp.nl>')

    def test_get_sender_from_object(self):
        # Whitelist domain.
        self.mail_server.write(
            {"domain_whitelist": "therp.nl,kingdom.fr,imperiumromanum.org"}
        )
        # Check with default user and author (current user).
        main_company = self.env.ref("base.main_company")
        himiltrude = self.partner_himiltrude.sudo().with_company(main_company)
        # Make sure user and company from object used.
        email_from = self.env.user.sudo().get_company_aware_email(himiltrude)
        self.assertEqual(email_from, "charlemagne@imperiumromanum.org")
