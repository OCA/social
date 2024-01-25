from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    forwarding_partner_id = fields.Many2one(
        related="partner_id.forwarding_partner_id", readonly=False
    )

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["forwarding_partner_id"]

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["forwarding_partner_id"]
