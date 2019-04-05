# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from itertools import groupby


class MailMassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    def update_opt_out(self, email, list_ids, value):
        """Save unsubscription reason when opting out from mailing."""
        self.ensure_one()
        action = "unsubscription" if value else "subscription"
        subscription_model = self.env['mail.mass_mailing.list_contact_rel']
        opt_out_records = subscription_model.search([
            ('contact_id.email', '=ilike', email),
            ('list_id', 'in', list_ids),
            ('opt_out', '!=', value),
        ])
        model_name = 'mail.mass_mailing.contact'
        for contact, subscriptions in groupby(opt_out_records,
                                              lambda r: r.contact_id):
            mailing_list_ids = [r.list_id.id for r in subscriptions]
            # reason_id and details are expected from the context
            self.env["mail.unsubscription"].create({
                "email": email,
                "mass_mailing_id": self.id,
                "unsubscriber_id": "%s,%d" % (model_name, contact.id),
                'mailing_list_ids': [(6, False, mailing_list_ids)],
                "action": action,
            })
        return super().update_opt_out(email, list_ids, value)
