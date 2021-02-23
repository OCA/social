# Copyright 2016 Therp BV <http://therp.nl>
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
