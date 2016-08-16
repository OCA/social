# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields, _
from openerp.exceptions import Warning as UserError


class MailMassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    avoid_resend = fields.Boolean(
        string="Avoid resend",
        help="Avoid to send this mass mailing email twice "
             "to the same recipient")

    @api.model
    def get_recipients(self, mailing):
        res_ids = super(MailMassMailing, self).get_recipients(mailing)
        if mailing.avoid_resend:
            already_sent = self.env['mail.mail.statistics'].search([
                ('mass_mailing_id', '=', mailing.id),
                ('model', '=', mailing.mailing_model),
            ])
            res_ids = list(set(res_ids).difference(
                already_sent.mapped('res_id')))
            if not res_ids:
                raise UserError(_(
                    "There is no more recipients to send and 'Avoid resend' "
                    "option is enabled"))
        return res_ids
