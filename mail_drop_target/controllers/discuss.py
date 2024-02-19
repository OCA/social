# Copyright Nguyen Minh Chien (chien@trobz.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.mail.controllers.discuss import DiscussController


class DiscussControllerInherit(DiscussController):
    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(
        self, ufile, thread_id, thread_model, is_pending=False, **kwargs
    ):
        if not is_pending or is_pending == "false":
            # Add this point, make sure the message related to the uploaded
            # file does exist.
            resp = self.mail_attachment_upload_email(ufile, thread_id, thread_model)
            if resp:
                return resp

        return super().mail_attachment_upload(
            ufile, thread_id, thread_model, is_pending, **kwargs
        )

    def mail_attachment_upload_email(self, ufile, thread_id, thread_model):
        channel_member = request.env["mail.channel.member"]
        if thread_model == "mail.channel":
            channel_member = request.env[
                "mail.channel.member"
            ]._get_as_sudo_from_request_or_raise(
                request=request, channel_id=int(thread_id)
            )
        try:
            mail_resp = channel_member.env["ir.attachment"].read_mail_file_content(
                ufile.filename, ufile.read(), int(thread_id), thread_model
            )
            ufile.seek(0)
            if not mail_resp:
                return False
            responseData = {"email_upload": 1}
        except AccessError:
            responseData = {
                "error": _("You are not allowed to upload an attachment here.")
            }
        except UserError as err:
            responseData = {"error": str(err)}
        return request.make_json_response(responseData)
