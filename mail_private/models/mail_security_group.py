# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailSecurityGroup(models.Model):

    _name = 'mail.security.group'
    _description = 'Mail Security Group'

    name = fields.Char(required=True)
    model_ids = fields.Many2many(
        'ir.model'
    )
    group_ids = fields.Many2many(
        'res.groups'
    )
    button_name = fields.Char()
    icon = fields.Char()
    active = fields.Boolean(
        default=True
    )

    def _get_security_groups(self):
        vals = []
        for record in self:
            vals.append(record._get_security_group())
        return vals

    def _get_security_group(self):
        return {
            'id': self.id,
            'name': self.name,
            'button_name': self.button_name or self.name,
            'icon': self.icon,
        }
