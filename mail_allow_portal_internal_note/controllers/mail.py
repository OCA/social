# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import plaintext2html

from odoo.addons.portal.controllers.mail import PortalChatter, _message_post_helper


class PortalChatterExt(PortalChatter):
    def portal_can_see_internal_messages(self, res_model, res_id):
        user = request.env.user
        if not user.has_group("base.group_user") and (
            user.portal_see_internal_msg_own or user.portal_see_internal_msg_other
        ):
            Model = request.env[res_model]
            if hasattr(Model, "partner_id"):
                record_company = (
                    Model.browse(res_id).partner_id.sudo().commercial_partner_id
                )
                is_own_company = record_company == user.commercial_partner_id
                if user.portal_see_internal_msg_own and is_own_company:
                    return True
                if user.portal_see_internal_msg_other and not is_own_company:
                    return True
        return False

    @http.route()
    def portal_message_fetch(
        self, res_model, res_id, domain=False, limit=10, offset=0, **kw
    ):
        res = super().portal_message_fetch(
            res_model, res_id, domain=domain, limit=limit, offset=offset
        )
        if self.portal_can_see_internal_messages(res_model, res_id):
            Message = request.env["mail.message"]
            domain = expression.AND(
                [domain, [("model", "=", res_model), ("res_id", "=", res_id)]]
            )
            messages = (
                Message.sudo()
                .search(domain or [], limit=limit, offset=offset)
                .portal_message_format()
            )
            message_count = Message.search_count(domain)
            res.update({"messages": messages, "message_count": message_count})
        return res

    # /!\ Override of addons/portal controller
    # No extension hooks available to avoid it.
    # Copy of all the original code, and add the is_log_note support
    @http.route(
        ["/mail/chatter_post"],
        type="http",
        methods=["POST"],
        auth="public",
        website=True,
    )
    def portal_chatter_post(
        self,
        res_model,
        res_id,
        message,
        redirect=None,
        attachment_ids="",
        attachment_tokens="",
        **kw
    ):
        """Create a new `mail.message` with the given `message` and/or
        `attachment_ids` and redirect the user to the newly created message.

        The message will be associated to the record `res_id` of the model
        `res_model`. The user must have access rights on this target document or
        must provide valid identifiers through `kw`. See `_message_post_helper`.
        """
        url = (
            redirect
            or (
                request.httprequest.referrer
                and request.httprequest.referrer + "#discussion"
            )
            or "/my"
        )

        res_id = int(res_id)

        attachment_ids = [
            int(attachment_id)
            for attachment_id in attachment_ids.split(",")
            if attachment_id
        ]
        attachment_tokens = [
            attachment_token
            for attachment_token in attachment_tokens.split(",")
            if attachment_token
        ]
        self._portal_post_check_attachments(attachment_ids, attachment_tokens)

        if message or attachment_ids:
            # message is received in plaintext and saved in html
            if message:
                message = plaintext2html(message)
            post_values = {
                "res_model": res_model,
                "res_id": res_id,
                "message": message,
                "send_after_commit": False,
                "attachment_ids": False,  # will be added afterward
            }
            post_values.update(
                (fname, kw.get(fname)) for fname in self._portal_post_filter_params()
            )
            # Extension: add is_çlog_not support
            if kw.get("is_log_note"):
                post_values.update({"subtype_xmlid": "mail.mt_note"})
            message = _message_post_helper(**post_values)

            if attachment_ids:
                # sudo write the attachment to bypass the read access
                # verification in mail message
                record = request.env[res_model].browse(res_id)
                message_values = {"res_id": res_id, "model": res_model}
                attachments = record._message_post_process_attachments(
                    [], attachment_ids, message_values
                )

                if attachments.get("attachment_ids"):
                    message.sudo().write(attachments)

        return request.redirect(url)
