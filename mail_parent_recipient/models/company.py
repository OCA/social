# -*- coding: utf-8 -*-
# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    use_parent_mail_address = fields.Boolean(
        string="Use Parent Mail Address",
        help="When an email is sent, fallback to partner's parent email if no "
        "email is set on the recipient partner."
    )
