# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

import datetime

from openerp import models, fields, api


class MailMandrillEvent(models.Model):
    _name = 'mail.mandrill.event'
    _order = 'timestamp desc'
    _rec_name = 'event_type'

    timestamp = fields.Integer(string='Mandrill UTC timestamp', readonly=True)
    time = fields.Datetime(string='Mandrill time', readonly=True)
    date = fields.Date(string='Mandrill date', readonly=True)
    event_type = fields.Selection(string='Event type', selection=[
        ('send', 'Sent'),
        ('deferral', 'Deferral'),
        ('hard_bounce', 'Hard bounce'),
        ('soft_bounce', 'Soft bounce'),
        ('open', 'Opened'),
        ('click', 'Clicked'),
        ('spam', 'Spam'),
        ('unsub', 'Unsubscribed'),
        ('reject', 'Rejected'),
    ], readonly=True)
    url = fields.Char(string='Clicked URL', readonly=True)
    ip = fields.Char(string='User IP', readonly=True)
    user_agent = fields.Char(string='User agent', readonly=True)
    mobile = fields.Boolean(string='Is mobile?', readonly=True)
    os_family = fields.Char(string='Operating system family', readonly=True)
    ua_family = fields.Char(string='User agent family', readonly=True)
    ua_type = fields.Char(string='User agent type', readonly=True)
    user_country_id = fields.Many2one(string='User country', readonly=True,
                                      comodel_name='res.country')
    message_id = fields.Many2one(string='Message', readonly=True,
                                 comodel_name='mail.mandrill.message')

    def _country_search(self, country_code, state_name):
        country = False
        if country_code:
            country = self.env['res.country'].search([
                ('code', 'ilike', country_code),
            ])
        if not country and state_name:
            state = self.env['res.country.state'].search([
                ('name', 'ilike', state_name),
            ])
            if state:
                country = state.country_id

        if country:
            return country.id
        return False

    def _process_bounce(self, message, event, event_type):
        msg = event.get('msg')
        bounce_type = msg.get('bounce_description', False) if msg else False
        bounce_description = msg.get('diag', False) if msg else False
        message.write({
            'state': 'bounced',
            'bounce_type': bounce_type,
            'bounce_description': bounce_description,
        })
        ts = event.get('ts', 0)
        time = datetime.datetime.fromtimestamp(ts)
        return {
            'message_id': message.id,
            'event_type': event_type,
            'timestamp': ts,
            'time': time.strftime('%Y-%m-%d %H:%M:%S') if ts else False,
            'date': time.strftime('%Y-%m-%d') if ts else False,
        }

    def _process_status(self, message, event, event_type, state):
        message.write({
            'state': state,
        })
        ts = event.get('ts', 0)
        time = datetime.datetime.fromtimestamp(ts)
        return {
            'message_id': message.id,
            'event_type': event_type,
            'timestamp': ts,
            'time': time.strftime('%Y-%m-%d %H:%M:%S') if ts else False,
            'date': time.strftime('%Y-%m-%d') if ts else False,
        }

    def _process_action(self, message, event, event_type, state):
        message.write({
            'state': state,
        })
        ts = event.get('ts', 0)
        url = event.get('url', False)
        ip = event.get('ip', False)
        user_agent = event.get('user_agent', False)
        os_family = False
        ua_family = False
        ua_type = False
        mobile = False
        country_code = False
        state = False
        location = event.get('location')
        if location:
            country_code = location.get('country_short', False)
            state = location.get('region', False)
        ua_parsed = event.get('user_agent_parsed')
        if ua_parsed:
            os_family = ua_parsed.get('os_family', False)
            ua_family = ua_parsed.get('ua_family', False)
            ua_type = ua_parsed.get('type', False)
            mobile = ua_parsed.get('mobile', False)
        country_id = self._country_search(country_code, state)
        time = datetime.datetime.fromtimestamp(ts)
        return {
            'message_id': message.id,
            'event_type': event_type,
            'timestamp': ts,
            'time': time.strftime('%Y-%m-%d %H:%M:%S') if ts else False,
            'date': time.strftime('%Y-%m-%d') if ts else False,
            'user_country_id': country_id,
            'ip': ip,
            'url': url,
            'mobile': mobile,
            'user_agent': user_agent,
            'os_family': os_family,
            'ua_family': ua_family,
            'ua_type': ua_type,
        }

    @api.model
    def process_send(self, message, event):
        return self._process_status(message, event, 'send', 'sent')

    @api.model
    def process_deferral(self, message, event):
        return self._process_status(message, event, 'deferral', 'deferred')

    @api.model
    def process_hard_bounce(self, message, event):
        return self._process_bounce(message, event, 'hard_bounce')

    @api.model
    def process_soft_bounce(self, message, event):
        return self._process_bounce(message, event, 'soft_bounce')

    @api.model
    def process_open(self, message, event):
        return self._process_action(message, event, 'open', 'opened')

    @api.model
    def process_click(self, message, event):
        return self._process_action(message, event, 'click', 'opened')

    @api.model
    def process_spam(self, message, event):
        return self._process_status(message, event, 'spam', 'spam')

    @api.model
    def process_unsub(self, message, event):
        return self._process_status(message, event, 'unsub', 'unsub')

    @api.model
    def process_reject(self, message, event):
        return self._process_status(message, event, 'reject', 'rejected')
