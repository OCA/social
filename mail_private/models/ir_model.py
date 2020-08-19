# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    private_group_ids = fields.Many2many(
        'res.groups',
    )
    mail_group_ids = fields.Many2many(
        'mail.security.group'
    )
