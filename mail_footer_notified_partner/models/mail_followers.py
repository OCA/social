# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api
from odoo.tools.translate import _


class MailNotification(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _notify_by_email(
        self, message, force_send=False, send_after_commit=True,
        user_signature=True
    ):
        # we need to save the complete list of partners because
        # _message_notification_recipients builds recipients
        # grouped by users groups. Thus get_additional_footer would get a
        # partial list of recipients
        return super(
            MailNotification, self.with_context(notified_partners=self)
        )._notify_by_email(
            message, force_send=force_send,
            send_after_commit=send_after_commit,
            user_signature=user_signature
        )

    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        footer_recipients = self.env.context.get(
            'notified_partners', recipients) or recipients
        body += self.get_additional_footer(footer_recipients)
        return super(MailNotification, self).\
            _notify_send(body, subject, recipients, **mail_values)

    @api.model
    def get_additional_footer(self, recipients):
        recipients_name = [
            recipient.name for recipient in recipients
        ]
        additional_footer = u'<br /><small>%s%s.</small><br />' % \
                            (_('Also notified: '),
                             ', '.join(recipients_name))
        return additional_footer
