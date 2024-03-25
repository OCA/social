from odoo.tests.common import TransactionCase

from ..hooks import post_init_hook


class TestMailTemplateRestrictByDefault(TransactionCase):
    def test_init_hook(self):
        post_init_hook(self.env.cr, self.env.registry)
        self.assertEqual(
            self.env.ref("mail.group_mail_template_editor").users,
            self.env.ref("base.user_admin"),
        )
