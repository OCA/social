from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_tracking_show_aliases = fields.Boolean(
        related="company_id.mail_tracking_show_aliases",
        readonly=False,
    )
    mail_tracking_email_max_age_days = fields.Integer(
        "Max age in days of mail tracking email records",
        config_parameter="mail_tracking.mail_tracking_email_max_age_days",
        help="If set as positive integer enables the deletion of "
        "old mail tracking records to reduce the database size.",
    )
