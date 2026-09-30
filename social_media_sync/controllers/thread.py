# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.http import request, route

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class ThreadControllerSocial(ThreadController):
    def _prepare_result(self):
        """Return the author of the comment in the shape the client expects.

        The shape is the one ``mail`` gives every author it sends to the web
        client, so the dialog reads the comment published on the social media
        the same way it reads a message of a chatter.
        """
        partner = request.env.user.partner_id
        return {
            "author": partner.mail_partner_format(
                {"id": True, "name": True, "is_company": True, "user": {}}
            )[partner]
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
            comment = post.create_comment(post_data, context) or {}
            # The channel is the partner, so every dialog the user has open
            # hears every publication. Saying which publication the answer is
            # about is what lets a dialog tell its own comment from one
            # published somewhere else.
            comment["post_account_id"] = post.id
            request.env["bus.bus"]._sendone(
                request.env.user.partner_id, "comments", comment
            )
            return self._prepare_result()
        return super().mail_message_post(thread_model, thread_id, post_data, context)
