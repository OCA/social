# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from telegram import Bot
from io import BytesIO
import base64
from odoo.tools import html2plaintext
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
import logging

_logger = logging.getLogger(__name__)


class MailMessageTelegram(models.Model):
    _name = 'mail.message.telegram'
    _description = 'Telegram Message'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'

    # content
    mail_message_id = fields.Many2one(
        'mail.message', 'Mail Message', required=True,
        ondelete='cascade', index=True,
        auto_join=True
    )
    message_id = fields.Char(readonly=True)
    chat_id = fields.Many2one(
        'mail.telegram.chat',
        required=True,
    )
    state = fields.Selection([
        ('outgoing', 'Outgoing'),
        ('sent', 'Sent'),
        ('exception', 'Delivery Failed'),
        ('cancel', 'Cancelled'),
    ], 'Status', readonly=True, copy=False, default='outgoing')
    failure_reason = fields.Text(
        'Failure Reason', readonly=1,
        help="Failure reason. This is usually the exception thrown by the"
             " email server, stored to ease the debugging of mailing issues.")

    @api.multi
    def send(
        self, auto_commit=False, raise_exception=False, parse_mode='HTML'
    ):
        for record in self:
            record._send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                parse_mode=parse_mode
            )

    def _send(
        self, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        message = False
        try:
            bot = Bot(self.chat_id.token)
            chat = bot.get_chat(self.chat_id.chat_id)
            if self.body:
                message = chat.send_message(
                    html2plaintext(self.body), parse_mode=parse_mode)
            for attachment in self.attachment_ids:
                if attachment.mimetype.split('/')[0] == 'image':
                    new_message = chat.send_photo(
                        BytesIO(base64.b64decode(attachment.datas))
                    )
                else:
                    new_message = chat.send_document(
                        BytesIO(base64.b64decode(attachment.datas)),
                        filename=attachment.datas_fname
                    )
                if not message:
                    message = new_message
                _logger.info(attachment.read(['mimetype']))
        except Exception as exc:
            if raise_exception:
                raise MailDeliveryException(_(
                    'Unable to send the telegram message'
                ), exc)
            else:
                _logger.warning('Issue sending message with id %s: %s' % (
                    self.id, exc))
                self.write({'state': 'exception', 'failure_reason': exc})
        if message:
            self.write({
                'state': 'sent',
                'message_id': message.message_id,
                'failure_reason': False
            })
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self._cr.commit()

    @api.multi
    def mark_outgoing(self):
        return self.write({'state': 'outgoing'})

    @api.multi
    def cancel(self):
        return self.write({'state': 'cancel'})
