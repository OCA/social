# Copyright 2016-2019 Jairo Llopis <jairo.llopis@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import HttpCase


class UICase(HttpCase):
    def test_ui(self):
        """Test snippet behavior."""
        base = "odoo.__DEBUG__.services['web_tour.tour'].%s"
        run = base % "run('%s')"
        ready = base % "tours.%s.ready"
        tour = "mass_mailing_name_editor_and_public"
        self.browser_js("/", run % tour, ready % tour, login="admin")
