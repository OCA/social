# -*- coding: utf-8 -*-
# Copyright 2016-2017 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.http import root
from odoo.tests.common import HttpCase


class UICase(HttpCase):
    def test_ui(self):
        """Test snippet behavior."""
        tour = "odoo.__DEBUG__.services['web_tour.tour'].%s"
        # Admin edits home page and adds subscription snippet
        self.phantom_js(
            "/",
            tour % "run('mass_mailing_name_editor')",
            tour % "tours.mass_mailing_name_editor.ready",
            login="admin")
        # Forced log out
        root.session_store.delete(self.session)
        # Public user uses subscription snippet
        self.phantom_js(
            "/",
            tour % "run('mass_mailing_name_public')",
            tour % "tours.mass_mailing_name_public.ready")
