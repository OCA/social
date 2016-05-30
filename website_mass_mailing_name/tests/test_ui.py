# -*- coding: utf-8 -*-
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import HttpCase


class UICase(HttpCase):
    def test_ui(self):
        """Test snippet behavior."""
        self.phantom_js(
            "/",
            "openerp.Tour.run('mass_mailing_partner', 'test')",
            "openerp.Tour.tours.mass_mailing_partner",
            "admin")
