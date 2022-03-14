# Copyright 2019 Akretion <https://www.akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False):
        incoming_mails = self.filtered("fetchmail_server_id").with_context(
            sender_is_via=True
        )
        if incoming_mails:
            super(MailMail, incoming_mails).send(
                auto_commit=auto_commit, raise_exception=raise_exception
            )
        normal_mails = self.filtered(lambda s: not s.fetchmail_server_id)
        if normal_mails:
            super(MailMail, normal_mails).send(
                auto_commit=auto_commit, raise_exception=raise_exception
            )
        return True
