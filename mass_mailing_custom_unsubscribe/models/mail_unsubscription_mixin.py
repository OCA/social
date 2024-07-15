# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import Command, api, models


class MailUnsubscriptionMixin(models.AbstractModel):
    _name = "mail.unsubscription.mixin"
    _description = "Mail unsubscription common methods"

    @api.model
    def _unsubscription_context(self) -> tuple:
        mailing = self.env.context.get("mailing_id")
        res_id = self.env.context.get("unsubscription_res_id")
        if isinstance(mailing, int):
            mailing = self.env["mailing.mailing"].browse(mailing)
        return (mailing, res_id)

    def _track_mail_unsubscription(
        self,
        email: str,
        action: str,
        list_ids=None,
        reason_id: int = None,
        details: str = None,
    ):
        mailing, res_id = self._unsubscription_context()
        if not mailing or not res_id:
            return
        vals = {
            "email": email,
            "mass_mailing_id": mailing.id,
            "unsubscriber_id": f"{mailing.mailing_model_real},{res_id}",
            "action": action,
            "metadata": self.env.context.get("metadata"),
        }
        if list_ids:
            vals["mailing_list_ids"] = [Command.link(list.id) for list in list_ids]
        if reason_id:
            vals["reason_id"] = reason_id
            if details:
                vals["details"] = details
        return self.env["mail.unsubscription"].create(vals)
