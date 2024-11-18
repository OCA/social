# Copyright 2024 Tecnativa - Carlos López
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from odoo.addons.mail_gateway.tests.common import MailGatewayTestCase


@tagged("-at_install", "post_install")
class TestMailWhatsAppTemplate(MailGatewayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "gateway",
                "gateway_type": "whatsapp",
                "token": "token",
                "whatsapp_security_key": "key",
                "webhook_secret": "MY-SECRET",
                "member_ids": [(4, cls.env.user.id)],
            }
        )
        cls.new_template_response_data = {
            "id": "018273645",
            "status": "APPROVED",
        }
        cls.new_template_full_response_data = {
            "name": "new_template",
            "parameter_format": "POSITIONAL",
            "components": [
                {"type": "HEADER", "format": "TEXT", "text": "Header 1"},
                {"type": "BODY", "text": "Body 1"},
                {"type": "FOOTER", "text": "Footer changed"},
            ],
            "language": "es",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "018273645",
        }
        cls.template_1_data = {
            "name": "test_odoo_1",
            "parameter_format": "POSITIONAL",
            "components": [
                {"type": "HEADER", "format": "TEXT", "text": "Header 1"},
                {"type": "BODY", "text": "Body 1"},
                {"type": "FOOTER", "text": "Footer 1"},
            ],
            "language": "es",
            "status": "APPROVED",
            "category": "MARKETING",
            "id": "1234567890",
        }
        cls.template_2_data = {
            "name": "test_with_buttons",
            "parameter_format": "POSITIONAL",
            "components": [
                {"type": "HEADER", "format": "TEXT", "text": "Header 2"},
                {"type": "BODY", "text": "Body 2"},
                {
                    "type": "BUTTONS",
                    "buttons": [{"type": "QUICK_REPLY", "text": "Button 1"}],
                },
            ],
            "language": "es",
            "status": "APPROVED",
            "category": "MARKETING",
            "sub_category": "CUSTOM",
            "id": "0987654321",
        }
        cls.templates_download = {
            "data": [cls.template_1_data, cls.template_2_data],
        }

    def _make_meta_requests(self, url, json_data, status_code=200):
        """
        Simulate a fake request to the Meta API:
        :param json_data: Dictionary with the json data to return
        :param status_code: Status code expected
        :returns requests.Response object
        """
        response = requests.Response()
        response.status_code = status_code
        response._content = json.dumps(json_data).encode()
        response.url = url
        response.headers["Content-Type"] = "application/json"
        return response

    def test_download_templates(self):
        def _patch_request_post(url, *args, **kwargs):
            if "message_templates" in url:
                return self._make_meta_requests(url, self.templates_download)
            return original_get(url, *args, **kwargs)

        with self.assertRaisesRegex(
            UserError, "WhatsApp Account is required to import templates"
        ):
            self.gateway.button_import_whatsapp_template()
        self.gateway.whatsapp_account_id = "123456"
        original_get = requests.get
        with patch.object(requests, "get", _patch_request_post):
            self.gateway.button_import_whatsapp_template()
        self.assertEqual(self.gateway.whatsapp_template_count, 2)
        template_1 = self.gateway.whatsapp_template_ids.filtered(
            lambda t: t.template_uid == "1234567890"
        )
        self.assertTrue(template_1.is_supported)
        self.assertEqual(template_1.template_name, "test_odoo_1")
        self.assertEqual(template_1.category, "marketing")
        self.assertEqual(template_1.language, "es")
        self.assertEqual(template_1.state, "approved")
        self.assertEqual(template_1.header, "Header 1")
        self.assertEqual(template_1.body, "Body 1")
        self.assertEqual(template_1.footer, "Footer 1")
        template_2 = self.gateway.whatsapp_template_ids.filtered(
            lambda t: t.template_uid == "0987654321"
        )
        self.assertFalse(template_2.is_supported)
        self.assertEqual(template_2.template_name, "test_with_buttons")
        self.assertEqual(template_2.category, "marketing")
        self.assertEqual(template_2.language, "es")
        self.assertEqual(template_2.state, "approved")
        self.assertEqual(template_2.header, "Header 2")
        self.assertEqual(template_2.body, "Body 2")
        self.assertFalse(template_2.footer)
        self.assertFalse(template_2.is_supported)

    def test_export_template(self):
        def _patch_request_post(url, *args, **kwargs):
            if "message_templates" in url:
                return self._make_meta_requests(url, self.new_template_response_data)
            return original_post(url, *args, **kwargs)

        def _patch_request_get(url, *args, **kwargs):
            if "018273645" in url:
                return self._make_meta_requests(
                    url, self.new_template_full_response_data
                )
            return original_get(url, *args, **kwargs)

        original_post = requests.post
        original_get = requests.get
        self.gateway.whatsapp_account_id = "123456"
        new_template = self.env["mail.whatsapp.template"].create(
            {
                "name": "New template",
                "category": "marketing",
                "language": "es",
                "header": "Header 1",
                "body": "Body 1",
                "gateway_id": self.gateway.id,
            }
        )
        self.assertEqual(new_template.template_name, "new_template")
        with patch.object(requests, "post", _patch_request_post):
            new_template.button_export_template()
        self.assertTrue(new_template.template_uid)
        self.assertTrue(new_template.is_supported)
        self.assertFalse(new_template.footer)
        self.assertEqual(new_template.state, "approved")
        # sync templates, footer should be updated
        with patch.object(requests, "get", _patch_request_get):
            new_template.button_sync_template()
        self.assertEqual(new_template.footer, "Footer changed")
