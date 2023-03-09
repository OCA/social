# Copyright 2022-2023 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _cleanup_side_records(self):
        """Delete pending outgoing mails."""
        self.mail_ids.filtered(lambda mail: mail.state == "outgoing").unlink()
        return super()._cleanup_side_records()

    def _update_content(self, body, attachment_ids):
        """Let checker know about empty body."""
        _self = self.with_context(deleting=body == "")
        return super(MailMessage, _self)._update_content(body, attachment_ids)
