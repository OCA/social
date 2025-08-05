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
        domain = [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "!=", "user_notification"),
        ]
        result_data = result.get("data", {})
        has_messages = request.env["mail.message"]._has_messages_in_record(domain)
        if not result_data and has_messages:
            return result
        mail_messages = result_data.get("mail.message", [])
        if len(mail_messages) == 1 and not mail_messages[0].get("body"):
            return result
        result["data"].setdefault("mail.message", [])
        message = request.env["mail.message"]._generate_message(domain)
        if message:
            result["data"]["mail.message"].append(message)
            result["messages"].append(message["id"])

        return result
