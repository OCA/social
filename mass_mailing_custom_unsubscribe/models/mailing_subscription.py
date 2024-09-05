# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailingSubscription(models.Model):
    _name = "mailing.subscription"
    _inherit = ["mailing.subscription", "mail.unsubscription.mixin"]

    def _update_unsubscription_reason(self):
        mailing, res_id = self._unsubscription_context()
        if not mailing or not res_id or not self.opt_out_reason_id:
            return
        last_unsubscription = self.env["mail.unsubscription"]._fetch_last_unsubcription(
            mailing, res_id, "unsubscription"
        )
        details = self.env.context.get("details")
        if last_unsubscription:
            last_unsubscription.reason_id = self.opt_out_reason_id
            if details:
                last_unsubscription.details = details

    def write(self, vals):
        res = super().write(vals)
        if vals.get("opt_out_reason_id"):
            self._update_unsubscription_reason()
        return res
