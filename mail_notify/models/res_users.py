from odoo import fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    token_ids = fields.One2many('res.users.token', 'user_id')
