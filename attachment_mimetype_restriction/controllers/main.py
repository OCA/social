# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.mail.controllers.discuss import DiscussController
from odoo.addons.web.controllers.main import Binary


class BinaryExtended(Binary):
    @http.route()
    def upload_attachment(self, model, id, ufile, callback=None):
        response = super().upload_attachment(model, id, ufile, callback)
        mimetype_error = getattr(request, "mimetype_error", None)
        if mimetype_error:
            data = response.get_data(as_text=True)
            response.set_data(
                data.replace(
                    json.dumps(_("Something horrible happened")),
                    json.dumps(mimetype_error),
                    1,
                )
            )
        return response


class DiscussControllerExtended(DiscussController):
    @http.route("/mail/attachment/upload", methods=["POST"], type="http", auth="public")
    def mail_attachment_upload(
        self, ufile, thread_id, thread_model, is_pending=False, **kwargs
    ):
        try:
            return super().mail_attachment_upload(
                ufile, thread_id, thread_model, is_pending, **kwargs
            )
        except ValidationError as e:
            error_msg = str(e.args[0]) if e.args else str(e)
            attachmentData = {"error": error_msg}
            return request.make_response(
                data=json.dumps(attachmentData),
                headers=[("Content-Type", "application/json")],
            )
