# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from base64 import b64decode
try:
    from extract_msg import Message
except ImportError:
    Message = None
from odoo import _, api, exceptions, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_drop(self, model, message, custom_values=None,
                     save_original=False, strip_attachments=False,
                     thread_id=None):
        disable_notify_mail_drop_target = \
            self.env["ir.config_parameter"].sudo().get_param(
                "mail_drop_target.disable_notify", default=False)
        self_message_process = self
        if disable_notify_mail_drop_target:
            self_message_process = self_message_process.with_context(
                message_create_from_mail_mail=True)
        result = self_message_process.message_process(
            model, message, custom_values=custom_values,
            save_original=save_original, strip_attachments=strip_attachments,
            thread_id=thread_id
        )
        if not result:
            return self.message_drop_existing(
                model, message, custom_values=custom_values,
                save_original=save_original,
                strip_attachments=strip_attachments, thread_id=thread_id
            )
        return result

    @api.model
    def message_drop_existing(self, model, message,
                              custom_values=None, save_original=False,
                              strip_attachments=False, thread_id=None):
        message = _("This message is already imported.")
        raise exceptions.Warning(message)

    @api.model
    def message_process_msg(
            self, model, message, custom_values=None, save_original=False,
            strip_attachments=False, thread_id=None,
    ):
        """Convert message to RFC2822 and pass to message_process"""
        if not Message:
            raise exceptions.UserError(
                _('Install the msg-extractor library to handle .msg files')
            )
        message_msg = Message(b64decode(message))
        message_email = self.env['ir.mail_server'].build_email(
            message_msg.sender, message_msg.to.split(','), message_msg.subject,
            # prefer html bodies to text
            message_msg._getStream('__substg1.0_10130102') or message_msg.body,
            email_cc=message_msg.cc,
            headers={'date': message_msg.date},
            message_id=message_msg.message_id,
            attachments=[
                (attachment.longFilename, attachment.data)
                for attachment in message_msg.attachments
            ],
        )
        return self.message_drop(
            model, message_email.as_string(), custom_values=custom_values,
            save_original=save_original, strip_attachments=strip_attachments,
            thread_id=thread_id,
        )
