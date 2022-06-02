# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import SavepointCase


class TestMailLayoutForce(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.layout_noop = cls.env.ref("mail_layout_force.mail_layout_noop")
        cls.layout_test = cls.env["ir.ui.view"].create(
            {
                "name": "Test Layout",
                "type": "qweb",
                "mode": "primary",
                "arch": "<t t-name='test'><h1></h1><t t-raw='message.body'/></t>",
            }
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Test Template",
                "body_html": "<p>Test</p>",
                "subject": "Test",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "auto_delete": False,
            }
        )
        cls.partner = cls.env.ref("base.res_partner_10")
        cls.partner.message_ids.unlink()
        cls.partner.message_subscribe([cls.partner.id])

    def test_noop_layout(self):
        self.template.force_email_layout_id = self.layout_noop
        self.partner.message_post_with_template(
            self.template.id,
            # This is ignored because the template has a force_email_layout_id
            email_layout_xmlid="mail.mail_notification_light",
        )
        message = self.partner.message_ids[-1]
        self.assertEqual(message.mail_ids.body_html.strip(), "<p>Test</p>")

    def test_custom_layout(self):
        self.template.force_email_layout_id = self.layout_test
        self.partner.message_post_with_template(
            self.template.id,
            # This is ignored because the template has a force_email_layout_id
            email_layout_xmlid="mail.mail_notification_light",
        )
        message = self.partner.message_ids[-1]
        self.assertEqual(message.mail_ids.body_html.strip(), "<h1></h1><p>Test</p>")

    def test_custom_layout_composer(self):
        self.template.force_email_layout_id = self.layout_test
        composer = (
            self.env["mail.compose.message"]
            .with_context(
                # This is ignored because the template has a force_email_layout_id
                custom_layout="mail.mail_notification_light"
            )
            .create(
                {
                    "res_id": self.partner.id,
                    "model": self.partner._name,
                    "template_id": self.template.id,
                }
            )
        )
        composer.onchange_template_id_wrapper()
        composer.send_mail()
        message = self.partner.message_ids[-1]
        self.assertEqual(message.mail_ids.body_html.strip(), "<h1></h1><p>Test</p>")
