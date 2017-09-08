# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    pyzor_server_ids = fields.Many2many(
        string='Pyzor Servers',
        comodel_name='pyzor.server',
        default=lambda s: s._default_pyzor_server_ids(),
        help='Enter the Pyzor Anti-SPAM servers that should be used for all '
             'messages received by this company.',
    )
    pyzor_account_ids = fields.Many2many(
        string='Pyzor Accounts',
        comodel_name='pyzor.account',
        help='Enter the Pyzor Anti-SPAM accounts that should be used for '
             'this company. Servers without an account selected will use '
             'anonymous authentication.'
    )

    @api.model
    def _default_pyzor_server_ids(self):
        return [
            (6, 0, self.env.ref('mail_spam.pyzor_server_public').ids),
        ]
