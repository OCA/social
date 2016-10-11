# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MailComposeMessage(models.TransientModel):

    _inherit = 'mail.compose.message'

    # The number of partner is needed to hide the 'print' button if
    # there is more than one partner
    partner_count = fields.Integer(
        string='Number of partners',
        compute='_compute_partner_count')

    @api.depends('partner_ids')
    def _compute_partner_count(self):
        for rec in self:
            rec.partner_count = len(rec.partner_ids)

    @api.multi
    def download_pdf(self):
        '''
        Download the email in pdf format, based on a QWeb report.
        '''
        self.ensure_one()
        if self.partner_count != 1:
            raise UserError(_("There must be only one recipient."))
        ctx = self.env.context.copy()
        ctx.update({'active_id': self.id,
                    'active_ids': [self.id],
                    'active_model': 'mail.compose.message'})

        return {
            'name': 'mail_as_letter',
            'model': 'mail.compose.message',
            'res_id': self.id,
            'type': 'ir.actions.report.xml',
            'report_name':
                'mail_as_letter.report_mail_print',
            'report_type': 'qweb-pdf',
            'context': ctx, }
