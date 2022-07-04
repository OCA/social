# © 2022 initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.mail import PortalChatter


class Chatter(PortalChatter):
    @http.route()
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        res = super().portal_chatter_post(res_model, res_id, message, **kw)
        thread = request.env[res_model].browse(res_id)
        thread.sudo().schedule_email_activity()
        return res
