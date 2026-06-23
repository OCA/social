# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    # email_to and email_cc already exist on mail.mail in 18.0 core.
    # email_bcc is not in core; define it here so bcc is preserved
    email_bcc = fields.Char("Bcc", help="Blind carbon copy message recipients")

    def _send(
        self,
        auto_commit=False,
        raise_exception=False,
        smtp_session=None,
        alias_domain_id=False,
        mail_server=False,
        post_send_callback=None,
    ):
        """Copy email_to, email_cc, email_bcc to mail.message before sending."""
        for mail in self.filtered(lambda r: r.state == "outgoing"):
            vals = {}
            for fname in ("email_to", "email_cc", "email_bcc"):
                raw = mail[fname]
                if not raw:
                    continue
                new_emails = tools.mail.email_normalize_all(raw)
                existing = mail.mail_message_id[fname]
                if existing:
                    new_emails += tools.mail.email_normalize_all(existing)
                deduped = list(dict.fromkeys(filter(None, new_emails)))
                if deduped:
                    vals[fname] = ",".join(deduped)
            if vals:
                mail.mail_message_id.write(vals)
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            alias_domain_id=alias_domain_id,
            mail_server=mail_server,
            post_send_callback=post_send_callback,
        )
