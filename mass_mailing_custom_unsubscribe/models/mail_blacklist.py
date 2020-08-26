# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailBlackList(models.Model):
    _inherit = "mail.blacklist"

    def _add(self, email):
        mailing_id = self.env.context.get("mailing_id")
        res_id = self.env.context.get("unsubscription_res_id")
        if mailing_id and res_id:
            mailing = self.env["mailing.mailing"].browse(mailing_id)
            model_name = mailing.mailing_model_real
            self.env["mail.unsubscription"].create(
                {
                    "email": email,
                    "mass_mailing_id": mailing_id,
                    "unsubscriber_id": "%s,%d" % (model_name, res_id),
                    "action": "blacklist_add",
                }
            )
        return super()._add(email)

    def _remove(self, email):
        mailing_id = self.env.context.get("mailing_id")
        res_id = self.env.context.get("unsubscription_res_id")
        if mailing_id and res_id:
            mailing = self.env["mailing.mailing"].browse(mailing_id)
            model_name = mailing.mailing_model_real
            self.env["mail.unsubscription"].create(
                {
                    "email": email,
                    "mass_mailing_id": mailing_id,
                    "unsubscriber_id": "%s,%d" % (model_name, res_id),
                    "action": "blacklist_rm",
                }
            )
        return super()._remove(email)
