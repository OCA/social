# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposeMessageReply(models.TransientModel):

    _inherit = "mail.compose.message"

    def send_mail(self, auto_commit=False):
        if self.env.context.get("reassign_to_parent"):
            for record in self:
                if record.model == "mail.message":
                    parent = self.env[record.model].browse(record.res_id)
                    record.model = parent.model
                    record.res_id = parent.res_id
                    record.parent_id = parent
        return super().send_mail(auto_commit=auto_commit)
