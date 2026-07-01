# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_mention_suggestion_option = fields.Selection(
        related="company_id.mail_mention_suggestion_option",
        readonly=False,
    )
