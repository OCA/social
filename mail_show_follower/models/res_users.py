from odoo import models, fields


class ResUser(models.Model):
    _inherit = "res.users"

    show_in_cc = fields.Boolean(
        string='Show in CC',
        default=True
    )
