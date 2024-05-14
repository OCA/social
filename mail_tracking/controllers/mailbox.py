# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.http import request, route

from odoo.addons.mail.controllers.mailbox import MailboxController


class MailTrackingMailBoxController(MailboxController):
    @route("/mail/failed/messages", methods=["POST"], type="json", auth="user")
    def discuss_failed_messages(
        self, search_term=None, before=None, after=None, limit=30, around=None
    ):
        """Fetch failed messages for discuss"""
        res = request.env["mail.message"]._message_fetch(
            [("is_failed_message", "=", True)],
            search_term=search_term,
            before=before,
            after=after,
            around=around,
            limit=limit,
        )
        return {**res, "messages": res["messages"].message_format()}
