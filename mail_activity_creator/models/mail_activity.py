# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivity(models.Model):

    _inherit = 'mail.activity'

    creator_uid = fields.Many2one(
        'res.users',
        default=lambda r: r.env.user.id,
        string="Creator",
    )
