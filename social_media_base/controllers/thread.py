# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.http import request, route

from odoo.addons.mail.controllers.thread import ThreadController


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

    @route("/mail/message/post", methods=["POST"], type="jsonrpc", auth="public")
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        guest = request.env["mail.guest"]._get_local_guest()

        if guest:
            request.update_context(guest_id=guest.id)

        context = request.context

        if thread_model == "social.post.account" and thread_id:
            post_id = request.env[thread_model].browse(thread_id)
            if post_id:
                comment = post_id.create_comment(post_data, context=context)

                target = request.env.user.partner_id or guest
                request.env["bus.bus"]._sendone(target, "comments", comment)

                return self._prepare_result()
            return None

        return super().mail_message_post(thread_model, thread_id, post_data, **kwargs)
