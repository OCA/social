# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import Command
from odoo.tests.common import TransactionCase


class TestMailLayoutForce(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].create(
            {
                "name": "Test QWeb View",
                "type": "qweb",
                "mode": "primary",
                "arch": "<div>Test</div>",
            }
        )
        cls.view_xml_id = "mail_layout_force.test_qweb_view"
        cls.env["ir.model.data"].create(
            {
                "module": "mail_layout_force",
                "name": "test_qweb_view",
                "model": "ir.ui.view",
                "res_id": cls.view.id,
            }
        )
        cls.mail_notification_layout = cls.env.ref("mail.mail_notification_layout")
        cls.layout_substitute = cls.env["ir.ui.view"].create(
            {
                "name": "Substitute Layout",
                "type": "qweb",
                "mode": "primary",
                "arch": """<?xml version="1.0"?>
                    <t t-name="custom_mail_notification_layout">
                    <div t-out="message.body"/>
                    <div t-if="signature" t-out="signature" style="font-size: 13px;"/>
                    <h1>Substituted</h1>
                </t>""",
            }
        )
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Test Template",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "force_email_layout_id": cls.view.id,
            }
        )
        cls.partner = cls.env.ref("base.res_partner_10")
        cls.partner.message_ids.unlink()
        cls.partner.message_subscribe([cls.partner.id])

    def test_chatter_message_uses_default_layout(self):
        self.partner.message_post(
            body="Test Message",
            email_layout_xmlid=self.mail_notification_layout.xml_id,
            message_type="email",
            subtype_xmlid="mail.mt_comment",
            mail_auto_delete=False,
            force_send=True,
        )
        message = self.partner.message_ids[-1]
        self.assertNotIn("<h1>Substituted</h1>", message.mail_ids.body_html)
        self.assertIn("Test Message", message.mail_ids.body_html)

    def test_chatter_message_uses_substituted_layout(self):
        self.mail_notification_layout.layout_mapping_line_ids = [
            Command.create({"substitute_layout_id": self.layout_substitute.id})
        ]
        self.partner.message_post(
            body="Test Message",
            email_layout_xmlid=self.mail_notification_layout.xml_id,
            message_type="email",
            subtype_xmlid="mail.mt_comment",
            mail_auto_delete=False,
            force_send=True,
        )
        message = self.partner.message_ids[-1]
        self.assertIn("<h1>Substituted</h1>", message.mail_ids.body_html)
        self.assertIn("Test Message", message.mail_ids.body_html)

    def test_inverse_method_sets_xmlid(self):
        self.assertEqual(self.template.email_layout_xmlid, self.view_xml_id)
        self.template.force_email_layout_id = False
        self.assertFalse(self.template.email_layout_xmlid)

    def test_compute_method_gets_view(self):
        self.template.email_layout_xmlid = self.view_xml_id
        self.assertEqual(self.template.force_email_layout_id, self.view)
        self.template.email_layout_xmlid = False
        self.assertFalse(self.template.force_email_layout_id)
