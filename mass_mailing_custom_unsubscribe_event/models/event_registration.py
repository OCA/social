# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EventRegistration(models.Model):
    _inherit = "event.registration"

    opt_out = fields.Boolean(
        string="Opt-Out",
        help="If opt-out is checked, this registree has refused to receive "
        "emails for mass mailing and marketing campaign.",
    )
    # No need of email field, as it already exists
