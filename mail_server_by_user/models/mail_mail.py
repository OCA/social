# Copyright 2022 ForgeFlow S.L. (https://forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models
from odoo.tools.mail import email_normalize


class MailMail(models.Model):

    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        mail_server_model = self.env["ir.mail_server"].sudo()
        for rec in self:
            if rec.email_from:
                mail_server_suggested = mail_server_model.search(
                    [("smtp_user", "=", email_normalize(rec.email_from))], limit=1
                )
                if (
                    mail_server_suggested
                    and rec.mail_server_id.id != mail_server_suggested.id
                ):
                    rec.mail_server_id = mail_server_suggested.id
        return super(MailMail, self)._send(auto_commit, raise_exception, smtp_session)
