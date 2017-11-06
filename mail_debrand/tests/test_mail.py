# -*- coding: utf-8 -*-
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


class SignatureCase(TransactionCase):
    def setUp(self):
        super(SignatureCase, self).setUp()
        self.user = self.env.ref("base.user_demo").with_context(lang="en_US")
        self.mail_notification = self.env["mail.notification"].with_context(
            lang="en_US")

    def signature(self, **context):
        """Get user's signature."""
        return (self.mail_notification.with_context(**context)
                .get_signature_footer(self.user.id))

    def test_signature_user_custom(self):
        """User name does not appear in signature when it is custom."""
        self.user.signature = u"¡Cüstom!"
        signature = self.signature()
        self.assertNotIn(self.user.name, signature)

    def test_signature_user_empty(self):
        """User name appears in signature by default."""
        self.user.signature = False
        signature = self.signature()
        self.assertIn(self.user.name, signature)

    def test_signature_user_skip(self):
        """User signature is skipped."""
        self.user.signature = "Skip me."
        signature = self.signature(skip_signature_user=True)
        self.assertNotIn(self.user.signature, signature)

    def test_signature_company_website_custom(self):
        """Company website link appears in signature."""
        sites = (
            "HTTP://EXAMPLE.COM",
            "http://example.com",
            "https://example.com",
            "HTTPS://example.com,"
        )
        for site in sites:
            for url in (site, site[8:]):
                self.user.company_id.website = url
                signature = self.signature()
                self.assertIn(url, signature)
                self.assertIn(self.user.company_id.name, signature)

    def test_signature_company_website_empty(self):
        """Company website link does not appear in signature."""
        self.user.company_id.website = False
        signature = self.signature()
        self.assertNotIn("<a href", signature)
        self.assertIn(self.user.company_id.name, signature)

    def test_signature_company_skip(self):
        """Company signature is skipped."""
        self.user.company_id.website = "http://example.com"
        signature = self.signature(skip_signature_company=True)
        self.assertNotIn(self.user.company_id.website, signature)

    def test_unbranded(self):
        """No Odoo branding found."""
        signature = self.signature()
        self.assertNotIn("using", signature)
        self.assertNotIn("odoo.com", signature)
        self.assertNotIn("Odoo", signature)
