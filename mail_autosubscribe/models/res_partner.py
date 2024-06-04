# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    mail_autosubscribe_ids = fields.Many2many(
        "mail.autosubscribe",
        string="Autosubscribe Models",
        column1="partner_id",
        column2="model_id",
    )
