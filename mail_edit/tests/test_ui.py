# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestMailEdit(odoo.tests.HttpCase):
    def test_tour(self):
        self.phantom_js(
            "/web",
            "odoo.__DEBUG__.services['web_tour.tour'].run('mail_edit_tour')",
            "odoo.__DEBUG__.services["
            "'web_tour.tour'].tours.mail_edit_tour.ready",
            login="demo",
        )
