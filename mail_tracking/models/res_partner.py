# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.bounced.mixin']

    # tracking_emails_count and email_score are non-store fields in order
    # to improve performance
    tracking_emails_count = fields.Integer(
        compute='_compute_tracking_emails_count', readonly=True)
    email_score = fields.Float(compute='_compute_email_score', readonly=True)

    @api.depends('email')
    def _compute_email_score(self):
        for partner in self.filtered('email'):
            partner.email_score = self.env['mail.tracking.email'].\
                email_score_from_email(partner.email)

    @api.multi
    @api.depends('email')
    def _compute_tracking_emails_count(self):
        for partner in self:
            count = 0
            if partner.email:
                count = self.env['mail.tracking.email'].search_count([
                    ('recipient_address', '=', partner.email.lower())
                ])
            partner.tracking_emails_count = count
