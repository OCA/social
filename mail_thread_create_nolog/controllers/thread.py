from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers import thread as mail_thread


class ThreadController(mail_thread.ThreadController):
    @http.route("/mail/thread/messages", methods=["POST"], type="json", auth="user")
    def mail_thread_messages(
        self,
        thread_model,
        thread_id,
        search_term=None,
        before=None,
        after=None,
        around=None,
        limit=30,
    ):
        result = super().mail_thread_messages(
            thread_model, thread_id, search_term, before, after, around, limit
        )

        result["data"].setdefault("mail.message", [])

        domain = [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "!=", "user_notification"),
        ]

        message = request.env["mail.message"]._generate_messsage(domain)

        if message:
            result["data"]["mail.message"].append(message)
            result["messages"].append(message["id"])

        return result
