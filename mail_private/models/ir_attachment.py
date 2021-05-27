# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    mail_group_id = fields.Many2one(
        'mail.security.group'
    )
