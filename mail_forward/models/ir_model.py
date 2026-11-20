from odoo import fields, models


class IrModel(models.Model):
    _inherit = "ir.model"

    enable_forward_to = fields.Boolean(
        help="Enable forwarding messages to records of this model."
    )
