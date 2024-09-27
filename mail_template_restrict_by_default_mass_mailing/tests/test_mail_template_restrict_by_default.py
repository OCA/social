from odoo.tests.common import TransactionCase

from ..hooks import post_init_hook


class TestMailTemplateRestrictByDefault(TransactionCase):
    def test_init_hook(self):
        post_init_hook(self.env.cr, self.env.registry)
        ref = self.env.ref
        self.assertNotIn(
            ref("mass_mailing.group_mass_mailing_user"),
            ref("base.default_user").groups_id,
        )
        self.assertNotIn(
            ref("mass_mailing.group_mass_mailing_user"), ref("base.user_demo").groups_id
        )
        self.assertIn(
            ref("mass_mailing.group_mass_mailing_user"),
            ref("base.user_admin").groups_id,
        )
