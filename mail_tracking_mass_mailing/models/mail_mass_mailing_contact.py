# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields


class MailMassMailingContact(models.Model):
    _name = 'mail.mass_mailing.contact'
    _inherit = ['mail.mass_mailing.contact', 'mail.bounced.mixin']

    email_score = fields.Float(
        string="Email score", readonly=True, store=False,
        compute='_compute_email_score')

    @api.multi
    @api.depends('email')
    def _compute_email_score(self):
        for contact in self.filtered('email'):
            contact.email_score = self.env['mail.tracking.email'].\
                email_score_from_email(contact.email)
