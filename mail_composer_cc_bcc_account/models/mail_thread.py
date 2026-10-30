# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_create(self, values_list):
        context = self.env.context
        res = super()._message_create(values_list)
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res.recipient_cc_ids = partners_cc
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res.recipient_bcc_ids = partners_bcc
        return res
