from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    show_internal_users_cc = fields.Boolean(
        string="Show Internal Users CC",
        related="company_id.show_internal_users_cc",
        readonly=False,
    )
