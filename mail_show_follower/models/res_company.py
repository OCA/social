from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    show_internal_users_cc = fields.Boolean(
        string='Show Internal Users CC',
        default=True
    )
