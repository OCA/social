# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.tools import consteq

from odoo.addons.mass_mailing.controllers.main import MassMailController


class MassMailSubscriptionEmailController(MassMailController):
    @http.route(
        "/mail/mailing/contact/<int:res_id>/unsubscribe",
        type="http",
        website=True,
        auth="public",
    )
    def mailing_contact_unsubscribe(self, res_id, email=None, token="", **post):
        subscription = request.env["mailing.contact.subscription"].sudo().browse(res_id)
        if not subscription.exists():  # pragma: no cover
            return request.redirect("/web")
        if not consteq(subscription._unsubscribe_token(), token):  # pragma: no cover
            raise AccessDenied()
        subscription.opt_out = True
        values = {"email": email}
        return request.render("mass_mailing.page_unsubscribed", values)
