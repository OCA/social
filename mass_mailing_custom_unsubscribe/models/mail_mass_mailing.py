# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from itertools import groupby

from odoo import models, tools
from odoo.tools.safe_eval import safe_eval


class MailMassMailing(models.Model):
    _inherit = "mailing.mailing"

    def update_opt_out(self, email, list_ids, value):
        """Save unsubscription reason when opting out from mailing."""
        self.ensure_one()
        action = "unsubscription" if value else "subscription"
        subscription_model = self.env["mailing.contact.subscription"]
        opt_out_records = subscription_model.search(
            [
                ("contact_id.email", "=ilike", email),
                ("list_id", "in", list_ids),
                ("opt_out", "!=", value),
            ]
        )
        model_name = "mailing.contact"
        for contact, subscriptions in groupby(opt_out_records, lambda r: r.contact_id):
            mailing_list_ids = [r.list_id.id for r in subscriptions]
            # reason_id and details are expected from the context
            self.env["mail.unsubscription"].create(
                {
                    "email": email,
                    "mass_mailing_id": self.id,
                    "unsubscriber_id": "%s,%d" % (model_name, contact.id),
                    "mailing_list_ids": [(6, False, mailing_list_ids)],
                    "action": action,
                }
            )
        return super().update_opt_out(email, list_ids, value)

    def update_opt_out_other(self, email, res_ids, value):
        """Method for changing unsubscription for models with opt_out field."""
        model = self.env[self.mailing_model_real].with_context(active_test=False)
        action = "unsubscription" if value else "subscription"
        if "opt_out" in model._fields:
            email_fname = "email_from"
            if "email" in model._fields:
                email_fname = "email"
            records = model.search(
                [("id", "in", res_ids), (email_fname, "ilike", email)]
            )
            records.write({"opt_out": value})
            for res_id in res_ids:
                self.env["mail.unsubscription"].create(
                    {
                        "email": email,
                        "mass_mailing_id": self.id,
                        "unsubscriber_id": "%s,%d" % (self.mailing_model_real, res_id),
                        "action": action,
                    }
                )

    def _get_opt_out_list(self):
        """Handle models with opt_out field for excluding them."""
        self.ensure_one()
        model = self.env[self.mailing_model_real].with_context(active_test=False)
        if self.mailing_model_real != "mailing.contact" and "opt_out" in model._fields:
            email_fname = "email_from"
            if "email" in model._fields:
                email_fname = "email"
            domain = safe_eval(self.mailing_domain)
            domain = [("opt_out", "=", True)] + domain
            recs = self.env[self.mailing_model_real].search(domain)
            normalized_email = (tools.email_split(c[email_fname]) for c in recs)
            return {e[0].lower() for e in normalized_email if e}
        return super()._get_opt_out_list()
