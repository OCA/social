from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    notify_followers = fields.Boolean(default=True)
