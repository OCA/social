# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class Users(models.Model):
    _inherit = "res.users"

    # These are fields instead of groups,
    # because Portal User form does not present group selection boxes
    portal_see_internal_msg_own = fields.Boolean(
        string="See own company Internal Messages",
    )
    portal_see_internal_msg_other = fields.Boolean(
        string="See other company Internal Messages",
    )
