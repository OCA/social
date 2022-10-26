# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    email_cc = fields.Char(
        string="Cc", help="Carbon copy recipients (placeholders may be used here)"
    )

    def get_mail_values(self, res_ids):
        self.ensure_one()
        res = super().get_mail_values(res_ids)
        for r in res_ids:
            if self.email_cc:
                res[r]["email_cc"] = self.email_cc
        return res
