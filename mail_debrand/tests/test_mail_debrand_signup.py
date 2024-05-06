from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestMailDebrandSignup(TransactionCase):
    def _has_module(self):
        module = self.env["ir.module.module"].search([("name", "=", "auth_signup")])
        self.assertTrue(module)
        return module.state == "installed"

    def test_debrand_auth_signup_set_password_email(self):
        if not self._has_module():
            return
        template = self.env.ref(
            "auth_signup.set_password_email",
        )
        self.assertIn("www.odoo.com", template.body_html)
        self.assertIn("Accept invitation", template.body_html)
        self.assertIn("to discover the tool", template.body_html)

        mail_id = template.send_mail(self.env.user.id)
        body = self.env["mail.mail"].browse(mail_id).body_html

        # The essential button is preserved
        self.assertIn("Accept invitation", body)
        # But at least part of the branding was removed
        self.assertNotIn("www.odoo.com", body)
        self.assertNotIn("to discover the tool", body)
