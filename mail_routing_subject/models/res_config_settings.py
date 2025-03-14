# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mail_routing_subject_prefixes = fields.Char(
        string="Reply prefixes",
        help="Space separated list of prefixes that mark a subject as a reply",
        config_parameter="mail_routing_subject.prefixes",
    )
