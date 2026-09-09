# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class MailGatewayInstagramContent(http.Controller):
    @http.route(
        "/mail_gateway_instagram/content/<int:attachment_id>/"
        "<string:access_token>/<string:filename>",
        type="http",
        auth="public",
        methods=["GET"],
    )
    def instagram_content(self, attachment_id, access_token, filename, **kwargs):
        """Serve one outbound attachment for Meta's Send Messages fetch.

        Graph 2018007 is a failed download of ``payload.url``. Query
        strings on ``/web/content`` are not fetched reliably; this path
        carries the token and the filename extension with no query
        string. The route is not readonly so a replica cannot miss a
        token committed just before the Graph POST.

        :param int attachment_id: ``ir.attachment`` id
        :param str access_token: attachment access token
        :param str filename: filename segment for Meta's extension check
        :return: file HTTP response
        :rtype: odoo.http.Response
        """
        del kwargs
        attachment = request.env["ir.attachment"].sudo().browse(attachment_id).exists()
        if not attachment:
            raise request.not_found()
        try:
            attachment.validate_access(access_token)
        except AccessError as err:
            raise request.not_found() from err
        try:
            _graph_type, canonical_mimetype = request.env[
                "mail.gateway.instagram"
            ]._instagram_classify_outbound_attachment(attachment)
        except UserError as err:
            raise request.not_found() from err
        stream = request.env["ir.binary"]._get_stream_from(
            attachment, filename=filename, mimetype=canonical_mimetype
        )
        stream.public = True
        return stream.get_response()
