# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    email_bounced = fields.Boolean(string="Email bounced")
    email_score = fields.Float(
        string="Email score", readonly=True, store=False,
        compute='_compute_email_score')

    @api.multi
    @api.depends('email')
    def _compute_email_score(self):
        for contact in self.filtered('email'):
            contact.email_score = self.env['mail.tracking.email'].\
                email_score_from_email(contact.email)

    @api.multi
    def email_bounced_set(self, tracking_emails, reason, event=None):
        contacts = self.filtered(lambda r: not r.email_bounced)
        return contacts.write({'email_bounced': True})

    @api.multi
    def write(self, vals):
        email = vals.get('email')
        if email is not None:
            vals['email_bounced'] = (
                bool(email) and
                self.env['mail.tracking.email'].email_is_bounced(email))
        return super(MailMassMailingContact, self).write(vals)
