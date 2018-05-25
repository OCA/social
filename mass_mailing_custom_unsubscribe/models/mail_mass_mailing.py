# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailMassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    def update_opt_out(self, email, res_ids, value):
        """Save unsubscription reason when opting out from mailing."""
        self.ensure_one()
        model = self.env[self.mailing_model_real].with_context(
            active_test=False)
        action = "unsubscription" if value else "subscription"
        records = self.env[model._name].browse(res_ids)
        previous = self.env["mail.unsubscription"].search(limit=1, args=[
            ("mass_mailing_id", "=", self.id),
            ("email", "=", email),
            ("action", "=", action),
        ])
        if 'opt_out' not in model._fields:
            return super(MailMassMailing, self).update_opt_out(
                email, res_ids, value)
        for one in records:
            # Store action only when something changed, or there was no
            # previous subscription record
            if one.opt_out != value or (action == "subscription" and
                                        not previous):
                # reason_id and details are expected from the context
                self.env["mail.unsubscription"].create({
                    "email": email,
                    "mass_mailing_id": self.id,
                    "unsubscriber_id": "%s,%d" % (one._name, one.id),
                    "action": action,
                })
            if model._name == 'mail.mass_mailing.contact':
                pass
        return super(MailMassMailing, self).update_opt_out(
            email, res_ids, value)
