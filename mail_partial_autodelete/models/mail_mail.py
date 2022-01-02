# Copyright 2021 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        self = self.with_context(autodelete_skip_unlink=True)
        return super()._send(auto_commit, raise_exception, smtp_session)

    def unlink(self):
        if self.env.context.get("autodelete_skip_unlink"):
            if self.env["ir.config_parameter"].get_param(
                "mail_partial_autodelete_debugmode"
            ):
                return self.write({"state": "sent"})  # prevent further operations
            # We only want to keep a trace of sent email during a grace period
            # exceptions email can be drop
            sent_records = self.filtered(lambda s: s.state == "sent")
            # we purge (for security reason) email that are not a notification
            # maybe we have secret inside
            sent_records.filtered(lambda s: not s.notification).write(
                {"body_html": "", "body": ""}
            )
            return super(MailMail, self - sent_records).unlink()
        else:
            return super().unlink()
