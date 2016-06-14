# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime

from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class MailTrackingEvent(models.Model):
    _name = "mail.tracking.event"
    _order = 'timestamp desc'
    _rec_name = 'event_type'
    _description = 'MailTracking event'

    recipient = fields.Char(string="Recipient", readonly=True)
    timestamp = fields.Float(
        string='UTC timestamp', readonly=True,
        digits=dp.get_precision('MailTracking Timestamp'))
    time = fields.Datetime(string="Time", readonly=True)
    date = fields.Date(
        string="Date", readonly=True, compute="_compute_date", store=True)
    tracking_email_id = fields.Many2one(
        string='Message', readonly=True,
        comodel_name='mail.tracking.email')
    event_type = fields.Selection(string='Event type', selection=[
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('deferral', 'Deferral'),
        ('hard_bounce', 'Hard bounce'),
        ('soft_bounce', 'Soft bounce'),
        ('open', 'Open'),
        ('click', 'Clicked'),
        ('spam', 'Spam'),
        ('unsub', 'Unsubscribed'),
        ('reject', 'Rejected'),
    ], readonly=True)
    smtp_server = fields.Char(string='SMTP server', readonly=True)
    url = fields.Char(string='Clicked URL', readonly=True)
    ip = fields.Char(string='User IP', readonly=True)
    user_agent = fields.Char(string='User agent', readonly=True)
    mobile = fields.Boolean(string='Is mobile?', readonly=True)
    os_family = fields.Char(string='Operating system family', readonly=True)
    ua_family = fields.Char(string='User agent family', readonly=True)
    ua_type = fields.Char(string='User agent type', readonly=True)
    user_country_id = fields.Many2one(string='User country', readonly=True,
                                      comodel_name='res.country')

    @api.multi
    @api.depends('time')
    def _compute_date(self):
        for email in self:
            email.date = fields.Date.to_string(
                fields.Date.from_string(email.time))

    def _process_action(self, tracking_email, metadata, event_type, state):
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        tracking_email.sudo().write({'state': state})
        return {
            'recipient': metadata.get('recipient', tracking_email.recipient),
            'timestamp': metadata.get('ts', ts),
            'time': metadata.get('time', fields.Datetime.to_string(dt)),
            'date': metadata.get('date', fields.Date.to_string(dt)),
            'tracking_email_id': tracking_email.id,
            'event_type': event_type,
            'ip': metadata.get('ip', False),
            'user_agent': metadata.get('user_agent', False),
            'mobile': metadata.get('mobile', False),
            'os_family': metadata.get('os_family', False),
            'ua_family': metadata.get('ua_family', False),
            'ua_type': metadata.get('ua_type', False),
            'user_country_id': metadata.get('user_country_id', False),
        }

    @api.model
    def process_open(self, tracking_email, metadata):
        return self._process_action(tracking_email, metadata, 'open', 'opened')
