from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    forwarding_partner_id = fields.Many2one(
        "res.partner",
        string="Forwarding Partner",
        help="Messages will be forwarded only for partners that are followers but no "
        "partners being notify because they belong to channel that is following the thread",
    )
