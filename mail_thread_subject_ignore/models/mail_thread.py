# Copyright 2023 ForgeFlow S.L. (www.forgeflow.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import email
import email.policy
import logging
import re
import xmlrpc.client as xmlrpclib

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def is_automated_reply(self, subject):
        automated_keywords = (
            self.env["mail.thread.subject.ignore"].search([]).mapped("name")
        )
        if not automated_keywords:
            return False
        pattern = re.compile(
            r"|".join(map(re.escape, automated_keywords)), re.IGNORECASE
        )
        if subject and pattern.search(subject):
            return True
        return False

    @api.model
    def message_process(
        self,
        model,
        message,
        custom_values=None,
        save_original=False,
        strip_attachments=False,
        thread_id=None,
    ):
        message_copy = message
        if isinstance(message, xmlrpclib.Binary):
            message = bytes(message.data)

        if isinstance(message, str):
            message = message.encode("utf-8")
        message = email.message_from_bytes(message, policy=email.policy.SMTP)
        msg_dict = self.message_parse(message, save_original=save_original)
        subject = msg_dict.get("subject")
        if self.is_automated_reply(subject):
            _logger.info(
                "Ignored mail from %s to %s with Message-Id %s",
                msg_dict.get("from"),
                msg_dict.get("to"),
                msg_dict.get("message_id"),
            )
            return None
        return super().message_process(
            model,
            message_copy,
            custom_values=custom_values,
            save_original=save_original,
            strip_attachments=strip_attachments,
            thread_id=thread_id,
        )
