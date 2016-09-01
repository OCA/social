# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    tracking_email_ids = fields.Many2many(
        string="Tracking emails", comodel_name="mail.tracking.email",
        readonly=True)
    email_score = fields.Float(
        string="Email score", readonly=True, default=50.0)

    @api.multi
    def email_score_calculate(self):
        for contact in self:
            contact.email_score = contact.tracking_email_ids.email_score()

    @api.multi
    def write(self, vals):
        email = vals.get('email')
        if email is not None:
            vals['tracking_email_ids'] = \
                self.env['mail.tracking.email']._tracking_ids_to_write(email)
        return super(MailMassMailingContact, self).write(vals)
