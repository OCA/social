# Copyright 2025 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from email.utils import parseaddr

from odoo.tests.common import SavepointCase


class CompanyAwareSenderCase(SavepointCase):
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
                "sequence": 99,
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
                    (6, 0, [cls.company_kingdom.id, cls.company_imperium.id]),
                ],
            }
        )
        cls.partner_himiltrude = cls.Partner.create(
            {
                "name": "Himiltrude",
                "email": "himiltrude@therp.nl",
                "user_id": cls.user_charles.id,
                "company_id": cls.company_imperium.id,
            }
        )

    def _assert_email(self, email_from, expected_email, expected_name=None):
        """Assert email_from matches expected parts, tolerant to quoting differences."""
        name, email = parseaddr(email_from or "")
        self.assertEqual(email, expected_email)
        if expected_name is not None:
            self.assertEqual(name, expected_name)
