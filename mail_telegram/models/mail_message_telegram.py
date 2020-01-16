# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import requests
import json
from odoo.tools import html2plaintext
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
import logging

_logger = logging.getLogger(__name__)


class MailMessageTelegram(models.Model):
    _name = 'mail.message.telegram'
    _inherits = {'mail.message': 'mail_message_id'}
    _order = 'id desc'
    _rec_name = 'subject'
    _base_url = 'https://api.telegram.org/bot'

    # content
    mail_message_id = fields.Many2one(
        'mail.message', 'Message', required=True,
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
        response_data = False
        try:
            url = '%s%s/sendMessage' % (self._base_url, self.chat_id.token)
            data = {'chat_id': self.chat_id.chat_id, 'text': html2plaintext(self.body)}
            if parse_mode:
                data['parse_mode'] = parse_mode
            response = requests.post(
                url, data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            response_data = json.loads(response.content.decode('utf-8'))
        except Exception as exc:
            if raise_exception:
                raise MailDeliveryException(_(
                    'Unable to send the telegram message'
                ), exc)
            else:
                _logger.warning('Issue sending message with id %s: %s' % (
                    self.id, exc))
                self.write({'state': 'exception', 'failure_reason': exc})
        if response_data:
            if response_data['ok']:
                self.write({
                    'state': 'sent',
                    'message_id': response_data['result']['message_id'],
                    'failure_reason': False
                })
                _logger.debug(
                    'Telegram message %s has been sended with id %s' % (
                        self.id, self.message_id
                    ))
            else:
                issue = _(
                    'The response from telegram was wrong: %s'
                ) % json.dumps(response_data)
                if raise_exception:
                    raise MailDeliveryException(issue, None)
                else:
                    _logger.warning('Issue sending message with id %s: %s' % (
                        self.id, issue))
                    self.write({
                        'state': 'exception',
                        'failure_reason': issue,
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
