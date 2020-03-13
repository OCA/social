# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    @api.constrains('email', 'list_ids')
    def _check_email_list_ids(self):
        for contact in self:
            lists = contact.subscription_list_ids.mapped('list_id')
            lists |= contact.list_ids
            others = lists.mapped('contact_ids') - contact

            contact_email = contact.email.strip().lower()
            other_emails = [e.strip().lower() for e in others.mapped('email')]
            if contact_email in other_emails:
                raise ValidationError(_(
                    "Cannot have the same email (%s) more"
                    "than once in the same list." % contact_email
                ))
