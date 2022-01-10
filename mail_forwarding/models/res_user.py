from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    forwarding_user_id = fields.Many2one("res.users", string="Forwarding User")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["forwarding_user_id"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["forwarding_user_id"]
