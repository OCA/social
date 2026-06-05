# Copyright 2026 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMailBulkSendWizard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["mail.template"].create(
            {
                "name": "Test Bulk Send Template",
                "model_id": cls.env["ir.model"]._get("res.partner").id,
                "subject": "Test Subject",
                "body_html": "<p>Hello</p>",
            }
        )
        cls.partner1 = cls.env["res.partner"].create(
            {"name": "Bulk Partner 1", "email": "p1@example.com"}
        )
        cls.partner2 = cls.env["res.partner"].create(
            {"name": "Bulk Partner 2", "email": "p2@example.com"}
        )

    def _make_wizard(self, partner_ids, template=None, active_model="res.partner"):
        template = template or self.template
        ctx = {
            "active_ids": partner_ids,
            "active_model": active_model,
            "default_template_id": template.id,
        }
        return (
            self.env["mail.bulk.send.wizard"]
            .with_context(**ctx)
            .create({"template_id": template.id})
        )

    def test_default_get_populates_active_ids_json(self):
        ctx = {
            "active_ids": [self.partner1.id, self.partner2.id],
            "active_model": "res.partner",
        }
        defaults = (
            self.env["mail.bulk.send.wizard"]
            .with_context(**ctx)
            .default_get(["active_ids_json", "active_model"])
        )
        self.assertEqual(
            json.loads(defaults["active_ids_json"]),
            [self.partner1.id, self.partner2.id],
        )
        self.assertEqual(defaults["active_model"], "res.partner")

    def test_action_send_success_closes_wizard(self):
        wizard = self._make_wizard([self.partner1.id, self.partner2.id])
        with patch.object(
            type(self.env["mail.template"]), "send_mail", return_value=1
        ) as mock_send:
            result = wizard.action_send()
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(result["type"], "ir.actions.act_window_close")

    def test_action_send_template_model_mismatch_raises_validation_error(self):
        other_template = self.env["mail.template"].create(
            {
                "name": "Users Template",
                "model_id": self.env["ir.model"]._get("res.users").id,
                "subject": "Hi",
                "body_html": "<p>Hi</p>",
            }
        )
        wizard = self._make_wizard(
            [self.partner1.id],
            template=other_template,
            active_model="res.partner",
        )
        with self.assertRaises(ValidationError):
            wizard.action_send()

    def test_action_send_skips_deleted_records(self):
        partner3 = self.env["res.partner"].create(
            {"name": "To Delete", "email": "del@example.com"}
        )
        deleted_id = partner3.id
        partner3.unlink()
        wizard = self._make_wizard([self.partner1.id, deleted_id])
        with patch.object(
            type(self.env["mail.template"]), "send_mail", return_value=1
        ) as mock_send:
            result = wizard.action_send()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(result["type"], "ir.actions.act_window_close")
