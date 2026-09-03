# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.http import request, route

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class ThreadControllerSocial(ThreadController):
    def _prepare_result(self):
        return {
            "author": {
                "id": request.env.user.partner_id.id,
                "name": request.env.user.partner_id.name,
                "is_company": request.env.user.partner_id.is_company,
                "user": {
                    "id": request.env.uid,
                    "isInternalUser": request.env.user._is_internal(),
                },
                "type": "partner",
            }
        }

    @route("/mail/message/post", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_message_post(self, thread_model, thread_id, post_data, context=None):
        if thread_model == "social.post.account" and thread_id:
            post = request.env[thread_model].browse(int(thread_id)).exists()
            if not post:
                return None
            post.check_access_rights("write")
            post.check_access_rule("write")
            comment = post.create_comment(post_data, context)
            request.env["bus.bus"]._sendone(
                request.env.user.partner_id, "comments", comment
            )
            return self._prepare_result()
        return super().mail_message_post(thread_model, thread_id, post_data, context)
