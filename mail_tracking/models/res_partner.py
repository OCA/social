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
        mt_obj = self.env['mail.tracking.email'].sudo()
        for partner in self.filtered('email'):
            partner.email_score = mt_obj.email_score_from_email(partner.email)

    @api.multi
    @api.depends('email')
    def _compute_tracking_emails_count(self):
        # We don't want performance issues due to heavy ACLs check for large
        # recordsets. Our option is to hide the number for regular users.
        if not self.env.user.has_group("base.group_system"):
            self.write({"tracking_emails_count": 0})
            return
        for partner in self:
            if partner.email:
                count = len(self.env['mail.tracking.email']._search([
                    ('recipient_address', '=', partner.email.lower())
                ]))
            partner.tracking_emails_count = count
