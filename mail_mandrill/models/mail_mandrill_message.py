# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

import datetime
import json
import logging

from openerp import models, fields, api

_logger = logging.getLogger(__name__)


class MailMandrillMessage(models.Model):
    _name = 'mail.mandrill.message'
    _order = 'timestamp desc'
    _rec_name = 'name'

    name = fields.Char(string='Subject', readonly=True)
    mandrill_id = fields.Char(string='Mandrill message ID', required=True,
                              readonly=True)
    timestamp = fields.Integer(string='Mandrill UTC timestamp', readonly=True)
    time = fields.Datetime(string='Mandrill time', readonly=True)
    date = fields.Date(string='Mandrill date', readonly=True)
    recipient = fields.Char(string='Recipient email', readonly=True)
    sender = fields.Char(string='Sender email', readonly=True)
    state = fields.Selection([
        ('deferred', 'Deferred'),
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('rejected', 'Rejected'),
        ('spam', 'Spam'),
        ('unsub', 'Unsubscribed'),
        ('bounced', 'Bounced'),
        ('soft-bounced', 'Soft bounced'),
    ], string='State', index=True, readonly=True,
        help=" * The 'Sent' status indicates that message was succesfully "
             "delivered to recipient Mail Exchange (MX) server.\n"
             " * The 'Opened' status indicates that message was opened or "
             "clicked by recipient.\n"
             " * The 'Rejected' status indicates that recipient email "
             "address is blacklisted by Mandrill. It is recomended to "
             "delete this email address.\n"
             " * The 'Spam' status indicates that Mandrill consider this "
             "message as spam.\n"
             " * The 'Unsubscribed' status indicates that recipient has "
             "requested to be unsubscribed from this message.\n"
             " * The 'Bounced' status indicates that message was bounced "
             "by recipient Mail Exchange (MX) server.\n"
             " * The 'Soft bounced' status indicates that message was soft "
             "bounced by recipient Mail Exchange (MX) server.\n")
    bounce_type = fields.Char(string='Bounce type', readonly=True)
    bounce_description = fields.Char(string='Bounce description',
                                     readonly=True)
    tags = fields.Char(string='Tags', readonly=True)
    metadata = fields.Text(string='Metadata', readonly=True)
    event_ids = fields.One2many(
        string='Mandrill events',
        comodel_name='mail.mandrill.event', inverse_name='message_id')

    def _message_prepare(self, message_id, event_type, event):
        msg = event.get('msg')
        ts = msg.get('ts', 0)
        time = datetime.datetime.fromtimestamp(ts)
        tags = msg.get('tags', [])
        metadata = msg.get('metadata', {})
        metatext = json.dumps(metadata, indent=4) if metadata else False
        return {
            'mandrill_id': message_id,
            'timestamp': ts,
            'time': time.strftime('%Y-%m-%d %H:%M:%S') if ts else False,
            'date': time.strftime('%Y-%m-%d') if ts else False,
            'recipient': msg.get('email', False),
            'sender': msg.get('sender', False),
            'name': msg.get('subject', False),
            'tags': ', '.join(tags) if tags else False,
            'metadata': metatext,
        }

    def _event_prepare(self, message, event_type, event):
        m_event = self.env['mail.mandrill.event']
        method = getattr(m_event, 'process_' + event_type, None)
        if method and hasattr(method, '__call__'):
            return method(message, event)
        else:
            _logger.info('Unknown event type: %s' % event_type)
        return False

    @api.model
    def process(self, message_id, event_type, event):
        if not (message_id and event_type and event):
            return False
        msg = event.get('msg')
        message = self.search([('mandrill_id', '=', message_id)])
        if msg and not message:
            data = self._message_prepare(message_id, event_type, event)
            message = self.create(data) if data else False
        if message:
            m_event = self.env['mail.mandrill.event']
            data = self._event_prepare(message, event_type, event)
            return m_event.create(data) if data else False
        return False
