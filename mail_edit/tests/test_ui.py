# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestMailEdit(odoo.tests.HttpCase):
    def test_tour(self):
        self.start_tour("/web", "mail_edit_tour", login="demo")
