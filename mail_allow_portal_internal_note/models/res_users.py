# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Users(models.Model):
    _inherit = "res.users"

    # These are fields instead of groups,
    # because Portal User form does not present group selection boxes
    portal_see_internal_msg_own = fields.Boolean(
        string="See own company Internal Messages",
        help="Portal User can see the internal messages"
        " for documents related to his parent company",
    )
    portal_see_internal_msg_other = fields.Boolean(
        string="See other company Internal Messages",
        help="Portal User can see the internal messages"
        " for documents related tho other companies"
        " , other than his parent company",
    )

    def portal_can_see_internal_messages(self, res_model, res_id):
        user = self.env.user
        if not user.has_group("base.group_user") and (
            user.portal_see_internal_msg_own or user.portal_see_internal_msg_other
        ):
            Model = self.env[res_model]
            if hasattr(Model, "partner_id"):
                record_company = Model.browse(res_id).partner_id.commercial_partner_id
                is_own_company = record_company == user.commercial_partner_id
                if user.portal_see_internal_msg_own and is_own_company:
                    return True
                if user.portal_see_internal_msg_other and not is_own_company:
                    return True
        return False
