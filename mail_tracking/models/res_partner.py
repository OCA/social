# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # tracking_emails_count and email_score are non-store fields in order
    # to improve performance
    # email_bounced is store=True and index=True field in order to filter
    # in tree view for processing bounces easier
    tracking_emails_count = fields.Integer(
        compute='_compute_tracking_emails_count', readonly=True)
    email_bounced = fields.Boolean(index=True)
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

    @api.multi
    def email_bounced_set(self, tracking_emails, reason, event=None):
        """Inherit this method to make any other actions to partners"""
        partners = self.filtered(lambda r: not r.email_bounced)
        return partners.write({'email_bounced': True})

    def write(self, vals):
        if 'email' not in vals:
            return super(ResPartner, self).write(vals)
        email = vals['email'].lower() if vals['email'] else False
        mte_obj = self.env['mail.tracking.email']
        if not mte_obj.email_is_bounced(email):
            vals['email_bounced'] = False
            return super(ResPartner, self).write(vals)
        res = mte_obj._email_last_tracking_state(email)
        tracking = mte_obj.browse(res[0].get('id'))
        event = tracking.tracking_event_ids[:1]
        self.email_bounced_set(tracking, event.error_details, event)
        return super(ResPartner, self).write(vals)
