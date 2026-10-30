from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    notify_followers = fields.Boolean(
        related="company_id.notify_followers",
        readonly=False,
    )
