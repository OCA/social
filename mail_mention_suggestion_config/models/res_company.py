# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    mail_mention_suggestion_option = fields.Selection(
        selection=[("users", "Users"), ("users_internal", "Internal Users")],
        help="Configures which type of partners will appear in your"
        " chatter messages mention suggestions. Possible values:\n"
        "- users: Will suggest partners that are related to any kind of users \n"
        "(internal, portal or public)."
        "- users_internal: Will only suggest partners related to internal users."
        "- None: Will suggest all partners, this is the default odoo option.",
    )
