# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from base64 import b64decode

import lxml.html

from odoo import _, api, exceptions, models
from odoo.tools import pycompat, ustr

try:
    from extract_msg import Message
except ImportError:
    Message = None


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_drop(
        self,
        model,
        message,
        custom_values=None,
        save_original=False,
        strip_attachments=False,
        thread_id=None,
    ):
        disable_notify_mail_drop_target = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_drop_target.disable_notify", default=False)
        )
        self_message_process = self
        if disable_notify_mail_drop_target:
            self_message_process = self_message_process.with_context(
                message_create_from_mail_mail=True
            )
        result = self_message_process.message_process(
            model,
            message,
            custom_values=custom_values,
            save_original=save_original,
            strip_attachments=strip_attachments,
            thread_id=thread_id,
        )
        if not result:
            return self.message_drop_existing(
                model,
                message,
                custom_values=custom_values,
                save_original=save_original,
                strip_attachments=strip_attachments,
                thread_id=thread_id,
            )
        return result

    @api.model
    def message_drop_existing(
        self,
        model,
        message,
        custom_values=None,
        save_original=False,
        strip_attachments=False,
        thread_id=None,
    ):
        message = _("This message is already imported.")
        raise exceptions.UserError(message)

    @api.model
    def message_process_msg(
        self,
        model,
        message,
        custom_values=None,
        save_original=False,
        strip_attachments=False,
        thread_id=None,
    ):
        """Convert message to RFC2822 and pass to message_process"""
        if not Message:
            raise exceptions.UserError(
                _("Install the msg-extractor library to handle .msg files")
            )
        message_msg = Message(b64decode(message))
        try:
            message_id = message_msg.messageId
        except AttributeError:
            # Using extract_msg < 0.24.4
            message_id = message_msg.message_id
        msg_body = message_msg.htmlBody or message_msg.body
        subtype = (
            lxml.html.fromstring(msg_body).find(".//*") is not None
            and "html"
            or "plain"
        )

        message_email = self.env["ir.mail_server"].build_email(
            message_msg.sender,
            message_msg.to.split(","),
            message_msg.subject,
            # prefer html bodies to text
            msg_body,
            email_cc=message_msg.cc,
            message_id=message_id,
            attachments=[
                (attachment.longFilename, attachment.data, attachment.mimetype)
                for attachment in message_msg.attachments
            ],
            subtype=subtype,
        )
        # We need to override message date, as an error rises when processing it
        # directly with headers
        key = pycompat.to_text(ustr("date"))
        del message_email[key]
        message_email[key] = message_msg.date
        return self.message_drop(
            model,
            message_email.as_string(),
            custom_values=custom_values,
            save_original=save_original,
            strip_attachments=strip_attachments,
            thread_id=thread_id,
        )

    def _notify_thread_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        mail_auto_delete=True,  # mail.mail
        model_description=False,
        force_email_company=False,
        force_email_lang=False,  # rendering
        resend_existing=False,
        force_send=True,
        send_after_commit=True,  # email send
        subtitles=None,
        **kwargs
    ):
        if self.env.context.get("message_create_from_mail_mail", False):
            return
        return super()._notify_thread_by_email(
            message,
            recipients_data,
            msg_vals=msg_vals,
            mail_auto_delete=mail_auto_delete,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            resend_existing=resend_existing,
            force_send=force_send,
            send_after_commit=send_after_commit,
            subtitles=subtitles,
            **kwargs,
        )
