# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import http
from odoo.http import request


class EmailBrowserViewController(http.Controller):

    @http.route(['/email/view/<string:token>'],
                type='http', auth='public', website=True)
    def email_view(self, token, **kwargs):
        record = request.env['mail.mail'].get_record_for_token(token)
        if not record:
            return request.not_found()
        return request.make_response(record.body_html)
