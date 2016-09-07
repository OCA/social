# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models


class MailMailStatistics(models.Model):
    _inherit = 'mail.mail.statistics'

    mass_mailing_sending_id = fields.Many2one(
        comodel_name='mail.mass_mailing.sending',
        string="Mass mailing sending", readonly=True)

    @api.model
    def create(self, vals):
        res = super(MailMailStatistics, self).create(vals)
        res.mass_mailing_sending_id = \
            self.env.context.get('mass_mailing_sending_id', False)
        return res
