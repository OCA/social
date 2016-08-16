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
        string="Email score",
        compute="_compute_email_score", store=True, readonly=True)

    @api.one
    @api.depends('tracking_email_ids', 'tracking_email_ids.state')
    def _compute_email_score(self):
        self.email_score = self.tracking_email_ids.email_score()

    @api.multi
    def write(self, vals):
        email = vals.get('email')
        if email is not None:
            vals['tracking_email_ids'] = \
                self.env['mail.tracking.email']._tracking_ids_to_write(email)
        return super(MailMassMailingContact, self).write(vals)
