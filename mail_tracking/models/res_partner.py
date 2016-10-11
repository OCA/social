# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tracking_emails_count = fields.Integer(
        string="Tracking emails count", readonly=True, store=False,
        compute="_compute_tracking_emails_count")
    email_bounced = fields.Boolean(string="Email bounced")
    email_score = fields.Float(
        string="Email score", readonly=True, store=False,
        compute='_compute_email_score')

    @api.multi
    @api.depends('email')
    def _compute_email_score(self):
        for partner in self.filtered('email'):
            partner.email_score = self.env['mail.tracking.email'].\
                email_score_from_email(partner.email)

    @api.multi
    @api.depends('email')
    def _compute_tracking_emails_count(self):
        for partner in self:
            partner.tracking_emails_count = self.env['mail.tracking.email'].\
                search_count([
                    ('recipient_address', '=ilike', partner.email)
                ])

    @api.multi
    def email_bounced_set(self, tracking_email, reason):
        """Inherit this method to make any other actions to partners"""
        return self.write({'email_bounced': True})

    @api.multi
    def write(self, vals):
        email = vals.get('email')
        if email is not None:
            vals['email_bounced'] = (
                bool(email) and
                self.env['mail.tracking.email'].email_is_bounced(email))
        return super(ResPartner, self).write(vals)
