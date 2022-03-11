from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    show_internal_users_cc = fields.Boolean(
        string="Show Internal Users CC", default=True
    )
