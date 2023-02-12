# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import http

from odoo.addons.mail.controllers.discuss import DiscussController


class MailTrackingDiscussController(DiscussController):
    @http.route()
    def mail_init_messaging(self):
        """Route used to initial values of Discuss app"""
        values = super().mail_init_messaging()
        values.update(
            {"failed_counter": http.request.env["mail.message"].get_failed_count()}
        )
        return values

    @http.route("/mail/failed/messages", methods=["POST"], type="json", auth="user")
    def discuss_failed_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return http.request.env["mail.message"]._message_fetch(
            domain=[("is_failed_message", "=", True)],
            max_id=max_id,
            min_id=min_id,
            limit=limit,
        )
