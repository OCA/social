# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from odoo.addons.portal.controllers.mail import PortalChatter


class PortalChatterExt(PortalChatter):
    def portal_can_see_internal_messages(self, res_model, res_id):
        user = request.env.user
        if not user.has_group("base.group_user") and (
            user.portal_see_internal_msg_own or user.portal_see_internal_msg_other
        ):
            Model = request.env[res_model]
            if hasattr(Model, "partner_id"):
                record_company = Model.browse(res_id).partner_id.commercial_partner_id
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
            res["messages"] = Message.search(
                domain or [], limit=limit, offset=offset
            ).portal_message_format()
            res["message_count"] = len(res["messages"])
        return res
