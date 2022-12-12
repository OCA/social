# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    main_mailing_list_id = fields.Many2one(
        "mailing.list",
        string="Company Newsletter",
        default=lambda self: self.env.ref(
            "mass_mailing.mailing_list_data",
            raise_if_not_found=False,
        ),
    )
