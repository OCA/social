from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    forwarding_partner_id = fields.Many2one(
        related="partner_id.forwarding_partner_id", readonly=False
    )

    def __init__(self, pool, cr):
        super().__init__(pool, cr)
        self.SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        self.SELF_WRITEABLE_FIELDS.append("forwarding_partner_id")
        self.SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        self.SELF_READABLE_FIELDS.append("forwarding_partner_id")
