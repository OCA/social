# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    message_group_ids = fields.Many2many(
        'mail.security.group',
        compute='_compute_message_group_ids'
    )

    @api.depends('groups_id')
    def _compute_message_group_ids(self):
        for record in self:
            record.message_group_ids = self.env['mail.security.group'].search([
                ('group_ids', 'in', record.groups_id.ids)
            ])
