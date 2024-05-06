# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_by_email_add_values(self, base_values):
        res = super()._notify_by_email_add_values(base_values)
        model = self.env["ir.model"].sudo().search([("model", "=", self._name)])
        custom_mailserver = model.outgoing_mailserver_id
        if custom_mailserver:
            res.update({"mail_server_id": custom_mailserver.id})
        custom_email = model.outgoing_email
        if custom_email:
            res.update({"email_from": custom_email})
        return res
