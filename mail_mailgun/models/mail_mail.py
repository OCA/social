# Copyright 2025 ForgeFlow
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    _inherit = "mail.mail"

    def send(self, auto_commit=False, raise_exception=False):
        for (
            mail_server_id,
            _smtp_from,
            batch_ids,
        ) in self._split_by_mail_configuration():

            mail_server = self.env["ir.mail_server"].browse(mail_server_id)
            if mail_server.smtp_authentication == "mailgun":
                self.mail_server_id = mail_server
                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=False,
                )
                _logger.info(
                    "Sent batch %s emails via mail server ID #%s",
                    len(batch_ids),
                    mail_server_id,
                )
            else:
                return super().send(
                    auto_commit=auto_commit, raise_exception=raise_exception
                )
