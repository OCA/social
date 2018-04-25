# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common


class TestMailDebrand(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestMailDebrand, cls).setUpClass()
        cls.template = cls.env.ref(
            'mail.mail_template_data_notification_email_default'
        )

    def test_generate_email_simple(self):
        res = self.template.generate_email(
            self.env.user.id, fields=['body_html'],
        )
        self.assertNotIn('using', res)

    def test_generate_email_multi(self):
        res = self.template.generate_email(
            self.env.user.ids, fields=['body_html'],
        )
        self.assertNotIn('using', res[[*res.keys()][0]])
