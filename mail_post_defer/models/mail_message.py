# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _cleanup_side_records(self):
        """Delete pending outgoing mails."""
        self.mail_ids.filtered(lambda mail: mail.state == "outgoing").unlink()
        self.env["mail.message.schedule"].search(
            [("mail_message_id", "in", self.ids)]
        ).unlink()
        return super()._cleanup_side_records()
