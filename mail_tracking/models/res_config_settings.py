from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_tracking_show_aliases = fields.Boolean(
        related="company_id.mail_tracking_show_aliases",
        readonly=False,
    )
