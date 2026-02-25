# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase


class TestIrConfigParameter(SavepointCase):
    def test_override_get_param(self):
        PARAM = "microsoft_outlook_client_identifier"
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param(PARAM, "test_client_id")
        no_preset_value = ICP.get_param(PARAM)
        self.assertEqual(no_preset_value, "test_client_id")
        preset_value = ICP.with_context(
            preset_microsoft_outlook_client_identifier="another_client_id",
        ).get_param(PARAM)
        self.assertEqual(preset_value, "another_client_id")
