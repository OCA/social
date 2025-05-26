# Copyright 2016,2025 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestMailTemplateQweb(TransactionCase):
    def test_email_template_qweb(self):
        template = self.env.ref("email_template_qweb.email_template_demo1")
        mail_values = template.generate_email([self.env.user.id], ["body_html"])
        self.assertTrue(
            # this comes from the called template if everything worked
            "<footer>" in mail_values[self.env.user.id]["body_html"],
            "Did not receive rendered template in response. Got: \n%s\n"
            % (mail_values[self.env.user.id]["body_html"]),
        )
        # the same method is also called in a non multi mode
        mail_values = template.generate_email(self.env.user.id, ["body_html"])
        self.assertTrue(
            # this comes from the called template if everything worked
            "<footer>" in mail_values["body_html"],
            "Did not receive rendered template in response. Got: \n%s\n"
            % (mail_values["body_html"]),
        )

    def test_editing(self):
        template = self.env.ref("email_template_qweb.email_template_demo1")
        template.edit_language = "en_US"
        self.assertIn("Dear", template.body_view_id.arch)
        self.assertIn("Dear", template.body_view_arch)
        template.body_view_arch = template.body_view_arch.replace("Dear", "Estimated")
        self.assertIn("Estimated", template.body_view_arch)
        self.assertIn("Estimated", template.body_view_id.arch)

    def test_copy(self):
        template = self.env.ref("email_template_qweb.email_template_demo1")
        template.edit_language = "en_US"
        self.assertIn("Dear", template.body_view_id.arch)
        self.assertIn("Dear", template.body_view_arch)
        copied_template = template.copy()
        self.assertNotEqual(template.body_view_id, copied_template.body_view_id)
        copied_template.body_view_arch = template.body_view_arch.replace(
            "Dear", "Beloved"
        )
        # Originals should not have changed.
        self.assertIn("Dear", template.body_view_id.arch)
        self.assertIn("Dear", template.body_view_arch)
        # Copied records should be changed now.
        self.assertIn("Beloved", copied_template.body_view_arch)
        self.assertIn("Beloved", copied_template.body_view_id.arch)
