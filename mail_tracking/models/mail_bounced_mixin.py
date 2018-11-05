# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MailBouncedMixin(models.AbstractModel):
    """ A mixin class to use if you want to add is_bounced flag on a model.
    The field '_primary_email' must be overridden in the model that inherit
    the mixin and must contain the email field of the model.
    """

    _name = 'mail.bounced.mixin'
    _description = 'Mail bounced mixin'
    _primary_email = ['email']

    email_bounced = fields.Boolean(index=True)

    @api.multi
    def email_bounced_set(self, tracking_emails, reason, event=None):
        """Inherit this method to make any other actions to the model that
        inherit the mixin"""
        partners = self.filtered(lambda r: not r.email_bounced)
        return partners.write({'email_bounced': True})

    def write(self, vals):
        [email_field] = self._primary_email
        if email_field not in vals:
            return super(MailBouncedMixin, self).write(vals)
        email = vals[email_field].lower() if vals[email_field] else False
        mte_obj = self.env['mail.tracking.email']
        if not mte_obj.email_is_bounced(email):
            vals['email_bounced'] = False
            return super(MailBouncedMixin, self).write(vals)
        res = mte_obj._email_last_tracking_state(email)
        tracking = mte_obj.browse(res[0].get('id'))
        event = tracking.tracking_event_ids[:1]
        self.email_bounced_set(tracking, event.error_details, event)
        return super(MailBouncedMixin, self).write(vals)
