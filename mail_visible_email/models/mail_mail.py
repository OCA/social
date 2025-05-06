# Copyright 2025 Therp BV <https://thero.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models, tools


def list_emails(partners):
    return [
        p.email and tools.mail._normalize_email(p.email) for p in partners if p.email
    ]


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        """Store email_to, email_cc, email_bcc also in mail.message."""
        for this in self.filtered(lambda r: r.state == "outgoing"):
            message_vals = {}
            email_values = this._get_email_values()
            for fieldname in ["email_to", "email_cc", "email_bcc"]:
                emails = email_values.get(fieldname, [])
                if not emails and not this[fieldname]:
                    continue
                message_vals[fieldname] = this._append_email(fieldname, emails)
            if message_vals:
                this.mail_message_id.write(message_vals)
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
        )

    def _get_email_values(self):
        self.ensure_one()
        partners_to = (
            self.recipient_ids - self.recipient_cc_ids - self.recipient_bcc_ids
        )
        return {
            "email_to": list_emails(partners_to),
            "email_cc": list_emails(self.recipient_cc_ids),
            "email_bcc": list_emails(self.recipient_bcc_ids),
        }

    def _append_email(self, fieldname, emails):
        """Do not override existing emails."""
        self.ensure_one()
        message = self.mail_message_id
        preset_emails = self[fieldname]
        if preset_emails:
            emails += tools.email_normalize_all(preset_emails)
        existing = message[fieldname]
        if existing:
            emails += existing.split(",")
        return ",".join(list(set(emails)))
