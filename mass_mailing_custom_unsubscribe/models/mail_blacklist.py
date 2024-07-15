# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class MailBlackList(models.Model):
    _name = "mail.blacklist"
    _inherit = ["mail.blacklist", "mail.unsubscription.mixin"]

    def _update_unsubscription_reason(self):
        mailing, res_id = self._unsubscription_context()
        if not mailing or not res_id or not self.opt_out_reason_id:
            return
        last_unsubscription = self.env["mail.unsubscription"]._fetch_last_unsubcription(
            mailing, res_id
        )
        details = self.env.context.get("details")
        if last_unsubscription:
            last_unsubscription.reason_id = self.opt_out_reason_id
            if details:
                last_unsubscription.details = details

    def _add(self, email, message=None):
        self._track_mail_unsubscription(email, "blacklist_add")
        return super()._add(email, message)

    def _remove(self, email, message=None):
        self._track_mail_unsubscription(email, "blacklist_rm")
        return super()._remove(email, message)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered("opt_out_reason_id"):
            record._update_unsubscription_reason()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("opt_out_reason_id"):
            self._update_unsubscription_reason()
        return res
