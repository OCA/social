# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tracking_email_ids = fields.Many2many(
        string="Tracking emails", comodel_name="mail.tracking.email",
        readonly=True)
    tracking_emails_count = fields.Integer(
        string="Tracking emails count", store=True, readonly=True,
        compute="_compute_tracking_emails_count")
    email_score = fields.Float(
        string="Email score",
        compute="_compute_email_score", store=True, readonly=True)

    @api.one
    @api.depends('tracking_email_ids.state')
    def _compute_email_score(self):
        self.email_score = self.tracking_email_ids.email_score()

    @api.one
    @api.depends('tracking_email_ids')
    def _compute_tracking_emails_count(self):
        self.tracking_emails_count = self.env['mail.tracking.email'].\
            search_count([
                ('recipient_address', '=ilike', self.email)
            ])

    @api.multi
    def write(self, vals):
        email = vals.get('email')
        if email is not None:
            vals['tracking_email_ids'] = \
                self.env['mail.tracking.email']._tracking_ids_to_write(email)
        return super(ResPartner, self).write(vals)
