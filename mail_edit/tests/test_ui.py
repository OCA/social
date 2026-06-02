# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl)

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMailEditTour(HttpCase):
    def setUp(self):
        super().setUp()

        self.partner = self.env["res.partner"].create(
            {
                "name": "Mail Edit Tour Partner",
            }
        )

        self.partner.message_post(
            body="<p>Message to move</p>",
            message_type="email",
            subtype_xmlid="mail.mt_comment",
        )

        self.partner_action = self.env["ir.actions.act_window"].create(
            {
                "name": "Mail Edit Partner Test",
                "res_model": "res.partner",
                "view_mode": "form",
                "target": "current",
            }
        )

    def test_mail_edit_move_message_tour(self):
        url = "/web#action=%s&id=%s&model=res.partner&view_type=form" % (
            self.partner_action.id,
            self.partner.id,
        )
        self.start_tour(
            url,
            "mail_edit_move_message_tour",
            login="admin",
        )
