# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestConfigurator(TransactionCase):
    def test_configurator(self):
        placeholder_obj = self.env["email.template.placeholder"]
        template_obj = self.env["mail.template"]
        partner_model_id = self.ref("base.model_res_partner")
        placeholders_vals = [
            {
                "name": "Salesperson name",
                "model_id": partner_model_id,
                "placeholder": "${object.user_id.partner_id.name}",
            },
            {
                "name": "Company vat",
                "model_id": partner_model_id,
                "placeholder": "${object.parent_id.vat}",
            },
        ]
        for vals in placeholders_vals:
            placeholder = placeholder_obj.create(vals)
            res = template_obj.onchange(
                {
                    "placeholder_id": placeholder.id,
                    "placeholder_value": False,
                },
                "placeholder_id",
                {
                    "placeholder_id": "1",
                    "placeholder_value": False,
                },
            )["value"]
            self.assertEqual(res["placeholder_value"], vals["placeholder"])
