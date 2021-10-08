# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import SavepointCase
from odoo.tools.misc import mute_logger


class TestMailDebrand(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_lang = "it_IT"
        cls.get_translated_paynow_arch_term()

        cls.default_arch = cls.env.ref(
            'mail.message_notification_email'
        ).arch
        cls.paynow_arch = cls.env.ref(
            'mail.mail_notification_paynow'
        ).arch

    @classmethod
    def get_translated_paynow_arch_term(cls):
        with mute_logger("odoo.tools.translate"):
            cls.env["res.lang"].load_lang(cls.other_lang)
            cls.env["base.update.translations"].create(
                {"lang": cls.other_lang}
            ).act_update()
        with mute_logger("odoo.addons.base.models.ir_translation"):
            cls.env["base.language.install"].create(
                {"lang": cls.other_lang, "overwrite": True}
            ).lang_install()

        paynow_template = cls.env.ref("mail.mail_notification_paynow")
        domain = [
            ("lang", "=", cls.other_lang),
            ("src", "like", "Powered by"),
            ("res_id", "=", paynow_template.id)
        ]
        cls.pb_term = cls.env["ir.translation"].search(domain).value
        cls.paynow_arch_translated = paynow_template.with_context(
            lang=cls.other_lang).arch

    def test_default_debrand(self):
        self.assertIn("using", self.default_arch)
        res = self.env["mail.template"]._debrand_body(self.default_arch)
        self.assertNotIn("using", res)

    def test_paynow_debrand(self):
        self.assertIn("Powered by", self.paynow_arch)
        res = self.env["mail.template"]._debrand_body(self.paynow_arch)
        self.assertNotIn("Powered by", res)

    def test_lang_paynow_debrand(self):
        self.assertIn(self.pb_term, self.paynow_arch_translated)
        res = self.env["mail.template"].with_context(lang=self.other_lang)\
            ._debrand_body(self.paynow_arch_translated)
        self.assertNotIn(self.pb_term, res)

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_template_lang_debranded_mail(self):
        partner = self.env['res.partner'].create({
            'name': 'test',
            'email': 'partner@testmail.com',
            'lang': self.other_lang,
        })
        model_id = self.env['ir.model'].search([
            ('model', '=', 'res.partner')
        ], limit=1)
        self.assertIn(self.pb_term, self.paynow_arch_translated)
        values = {
            'name': "New Template",
            'body_html': self.paynow_arch_translated,
            'partner_to': '${object.id}',
            'model_id': model_id.id,
        }
        template = self.env['mail.template'].create(values)
        ctx = {
            'default_template_id': template.id,
            'default_model': model_id.model,
            'default_res_id': partner.id
        }
        MailThread = self.env['mail.thread'].with_context(ctx)
        paynow_arch_debranded = MailThread._replace_local_links(
            self.paynow_arch_translated)
        self.assertIn(self.pb_term, paynow_arch_debranded)

        template.lang = "${object.lang}"
        paynow_arch_debranded = MailThread._replace_local_links(
            self.paynow_arch_translated)
        self.assertNotIn(self.pb_term, paynow_arch_debranded)
