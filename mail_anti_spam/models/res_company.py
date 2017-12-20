# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ResCompany(models.Model):

    _inherit = 'res.company'

    reverend_thomas_ids = fields.Many2many(
        string='SPAM Databases',
        comodel_name='reverend.thomas',
        default=lambda s: s._default_reverend_thomas_ids(),
        help='Enter the Anti-SPAM databases that should be used for all '
             'messages received by this company.',
    )

    @api.model
    def _default_reverend_thomas_ids(self):
        return [
            (6, 0, self.env.ref('mail_anti_spam.reverend_thomas_default').ids),
        ]
