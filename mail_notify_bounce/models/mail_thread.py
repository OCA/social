# -*- coding: utf-8 -*-
# Copyright 2017 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging
from odoo import models, api, tools, _
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def notify_bounce_partners(self, message, fetchmail, message_dict):
        message_id = message.get('Message-Id')
        email_from = tools.decode_message_header(message, 'From')
        email_from_localpart = (
            (
                tools.email_split(email_from) or ['']
            )[0].split('@', 1)[0].lower()
        )

        # same criteria used by odoo
        # see addons/mail/models/mail_thread.py
        if (
            message.get_content_type() == 'multipart/report' or
            email_from_localpart == 'mailer-daemon'
        ):

            references = tools.decode_message_header(message, 'References')
            in_reply_to = tools.decode_message_header(
                message, 'In-Reply-To').strip()
            thread_references = references or in_reply_to
            msg_references = [
                ref for ref in
                tools.mail_header_msgid_re.findall(thread_references) if
                'reply_to' not in ref
            ]
            MailMessage = self.env['mail.message']
            mail_messages = MailMessage.sudo().search([
                ('message_id', 'in', msg_references)], limit=1)
            recipients = mail_messages.mapped('author_id')
            recipients |= fetchmail.bounce_notify_partner_ids

            if not recipients:
                _logger.info(
                    'Not notifying bounce email from %s with Message-Id %s: '
                    'no recipients found',
                    email_from, message_id
                )
                return

            _logger.info(
                'Notifying bounce email from %s with Message-Id %s',
                email_from, message_id
            )
            email = self.env['mail.mail'].create({
                'body_html': (
                    u"%s<br/><br/><br/>%s<br/><br/>%s"
                    % (
                        ustr(message_dict['body']),
                        _("Raw message:"),
                        ustr(message.__str__()).replace(
                            "\n", "<br/>")
                    )),
                'subject': message_dict['subject'],
                'recipient_ids': [
                    (6, 0, [p.id for p in recipients])
                ]
            })
            email.send()

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None,
        custom_values=None
    ):
        if self.env.context.get('fetchmail_server_id'):
            fetchmail = self.env['fetchmail.server'].browse(
                self.env.context['fetchmail_server_id'])
            self.notify_bounce_partners(message, fetchmail, message_dict)

        return super(MailThread, self).message_route(
            message=message, message_dict=message_dict, model=model,
            thread_id=thread_id, custom_values=custom_values
        )
