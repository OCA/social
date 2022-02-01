# Copyright 2016-2019 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import os

from odoo import tools
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class UICase(HttpCase):
    def setUp(self):
        super().setUp()
        module_name = "website_mass_mailing_name"
        path = os.path.join(module_name, "tests", "snippet_test_page.xml")
        with tools.file_open(path) as fp:
            tools.convert_xml_import(self.env.cr, module_name, fp)

    def test_ui(self):
        """Test snippet behavior."""
        admin_mailing_contact = self.env["mailing.contact"].search(
            [("email", "=", "admin@yourcompany.example.com")],
        )
        if admin_mailing_contact:
            admin_mailing_contact.unlink()
        self.start_tour("/mass-mailing-name", "mass_mailing_name_admin", login="admin")
        self.start_tour("/mass-mailing-name", "mass_mailing_name_public", login=None)
