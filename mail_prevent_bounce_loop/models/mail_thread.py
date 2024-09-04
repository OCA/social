# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _routing_create_bounce_email(
        self, email_from, body_html, message, **mail_values
    ):
        partner = self._mail_find_partner_from_emails([email_from])
        if partner and partner[0].no_bounce_email:
            _logger.info("No bounce email sent to %s", email_from)
            return True
        super()._routing_create_bounce_email(
            email_from, body_html, message, **mail_values
        )

    def _notify_thread_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        mail_auto_delete=True,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        resend_existing=False,
        force_send=True,
        send_after_commit=True,
        subtitles=None,
        **kwargs,
    ):
        email_from = message.email_from
        email_from_partner = self._mail_find_partner_from_emails([email_from])
        if email_from_partner and email_from_partner[0].is_automatic_reply_address:
            _logger.info(
                "No notification sent to followers for email received from %s",
                email_from,
            )
            return True
        return super()._notify_thread_by_email(
            message,
            recipients_data,
            msg_vals,
            mail_auto_delete,
            model_description,
            force_email_company,
            force_email_lang,
            resend_existing,
            force_send,
            send_after_commit,
            subtitles,
            **kwargs,
        )
