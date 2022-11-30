# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Onestein - Andrea Stirpe
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests import common
from odoo.tools.misc import mute_logger


class TestMailDebrand(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.default_template = self.env.ref("mail.message_notification_email")
        self.paynow_template = self.env.ref("mail.mail_notification_paynow")

    def test_default_debrand(self):
        self.assertIn("using", self.default_template.arch)
        res = self.env["mail.template"]._render_template(
            self.default_template.arch, "ir.ui.view", [self.default_template]
        )
        self.assertNotIn("using", res)

    def test_paynow_debrand(self):
        self.assertIn("Powered by", self.paynow_template.arch)
        res = self.env["mail.template"]._render_template(
            self.paynow_template.arch, "ir.ui.view", [self.paynow_template]
        )
        self.assertNotIn("Powered by", res)

    def test_lang_paynow_debrand(self):
        with mute_logger("odoo.addons.base.models.ir_translation"):
            self.env["base.language.install"].create(
                {"lang": "nl_NL", "overwrite": True}
            ).lang_install()
        with mute_logger("odoo.tools.translate"):
            self.env["base.update.translations"].create({"lang": "nl_NL"}).act_update()
        ctx = dict(lang="nl_NL")
        paynow_arch = self.paynow_template.with_context(ctx).arch
        self.assertIn("Aangeboden door", paynow_arch)
        res = (
            self.env["mail.template"]
            .with_context(ctx)
            ._render_template(paynow_arch, "ir.ui.view", [self.paynow_template])
        )
        self.assertNotIn("Aangeboden door", res)
