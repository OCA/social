# Copyright 2020 Valentin Vinagre <valentin.vinagre@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, fields


class ResUser(models.Model):
    _inherit = "res.users"

    show_in_cc = fields.Boolean(
        string='Show in CC',
        default=True
    )
