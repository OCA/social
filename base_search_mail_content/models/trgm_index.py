# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# Copyright 2016 Serpent Consulting Services Pvt. Ltd.
# Copyright 2017 LasLabs Inc.
# Copyright 2018 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TrgmIndex(models.Model):
    _inherit = "trgm.index"

    # We take advantage of field inheritance to redefine help instead of do
    # inheritance in views that throws an error
    field_id = fields.Many2one(
        help="You can either select a field of type 'text', 'char' or 'html'."
    )
