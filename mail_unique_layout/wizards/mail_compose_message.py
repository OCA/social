# Copyright 2021 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposeMessage(models.TransientModel):

    _inherit = "mail.compose.message"

    def send_mail(self, auto_commit=False):
        if self.env.context.get("unique_layout_ctx_added"):
            return super().send_mail(auto_commit)
        return (
            super()
            .with_context(
                unique_layout_ctx_added=True,
                custom_layout="mail_unique_layout.test_layout",
            )
            .send_mail(auto_commit)
        )
