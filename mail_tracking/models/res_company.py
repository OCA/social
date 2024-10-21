from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mail_tracking_show_aliases = fields.Boolean(
        string="Show Aliases in Mail Tracking",
        default=False,
    )
