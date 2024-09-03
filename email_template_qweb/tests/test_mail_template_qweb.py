# Copyright 2016-2024 Therp BV <http://therp.nl>
# Copyright 2024 ForgeFlow S.L. (https://www.forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestMailTemplateQweb(TransactionCase):
    def test_email_template_qweb(self):
        template = self.env.ref("email_template_qweb.email_template_demo1")
        render_fields = ["body_html"]
        mail_values = template._generate_template([self.env.user.id], render_fields)
        self.assertTrue(
            "<footer>" in mail_values[self.env.user.id]["body_html"],
            "Did not receive rendered template in response. Got: \n{}".format(
                mail_values[self.env.user.id]["body_html"]
            ),
        )
        # the same method is also called in a non multi mode
        mail_values_single_mode = template._generate_template(
            [self.env.user.id], render_fields
        )
        self.assertTrue(
            "<footer>" in mail_values_single_mode[self.env.user.id]["body_html"],
            "Did not receive rendered template in response. Got: \n{}".format(
                mail_values_single_mode[self.env.user.id]["body_html"]
            ),
        )
