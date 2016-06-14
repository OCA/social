# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import urlparse
import time
from datetime import datetime

from openerp import models, api, fields, tools
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


class MailTrackingEmail(models.Model):
    _name = "mail.tracking.email"
    _order = 'time desc'
    _rec_name = 'name'
    _description = 'MailTracking email'

    name = fields.Char(string="Subject", readonly=True, index=True)
    timestamp = fields.Float(
        string='UTC timestamp', readonly=True,
        digits=dp.get_precision('MailTracking Timestamp'))
    time = fields.Datetime(string="Time", readonly=True)
    date = fields.Date(
        string="Date", readonly=True, compute="_compute_date", store=True)
    mail_message_id = fields.Many2one(
        string="Message", comodel_name='mail.message', readonly=True)
    mail_id = fields.Many2one(
        string="Email", comodel_name='mail.mail', readonly=True)
    partner_id = fields.Many2one(
        string="Partner", comodel_name='res.partner', readonly=True)
    recipient = fields.Char(string='Recipient email', readonly=True)
    sender = fields.Char(string='Sender email', readonly=True)
    state = fields.Selection([
        ('error', 'Error'),
        ('deferred', 'Deferred'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Open'),
        ('rejected', 'Rejected'),
        ('spam', 'Spam'),
        ('unsub', 'Unsubscribed'),
        ('bounced', 'Bounced'),
        ('soft-bounced', 'Soft bounced'),
    ], string='State', index=True, readonly=True, default=False,
        help=" * The 'Error' status indicates that there was an error "
             "when trying to sent the email, for example, "
             "'No valid recipient'\n"
             " * The 'Sent' status indicates that message was succesfully "
             "sent via outgoing email server (SMTP).\n"
             " * The 'Delivered' status indicates that message was "
             "succesfully delivered to recipient Mail Exchange (MX) server.\n"
             " * The 'Open' status indicates that message was opened or "
             "clicked by recipient.\n"
             " * The 'Rejected' status indicates that recipient email "
             "address is blacklisted by outgoing email server (SMTP). "
             "It is recomended to delete this email address.\n"
             " * The 'Spam' status indicates that outgoing email "
             "server (SMTP) consider this message as spam.\n"
             " * The 'Unsubscribed' status indicates that recipient has "
             "requested to be unsubscribed from this message.\n"
             " * The 'Bounced' status indicates that message was bounced "
             "by recipient Mail Exchange (MX) server.\n"
             " * The 'Soft bounced' status indicates that message was soft "
             "bounced by recipient Mail Exchange (MX) server.\n")
    error_smtp_server = fields.Char(string='Error SMTP server', readonly=True)
    error_type = fields.Char(string='Error type', readonly=True)
    error_description = fields.Char(
        string='Error description', readonly=True)
    bounce_type = fields.Char(string='Bounce type', readonly=True)
    bounce_description = fields.Char(
        string='Bounce description', readonly=True)
    tracking_event_ids = fields.One2many(
        string="Tracking events", comodel_name='mail.tracking.event',
        inverse_name='tracking_email_id', readonly=True)

    @api.multi
    @api.depends('time')
    def _compute_date(self):
        for email in self:
            email.date = fields.Date.to_string(
                fields.Date.from_string(email.time))

    def _get_mail_tracking_img(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        path_url = (
            'mail/tracking/open/%(db)s/%(tracking_email_id)s/blank.gif' % {
                'db': self.env.cr.dbname,
                'tracking_email_id': self.id,
            })
        track_url = urlparse.urljoin(base_url, path_url)
        return (
            '<img src="%(url)s" alt="" '
            'data-odoo-tracking-email="%(tracking_email_id)s"/>' % {
                'url': track_url,
                'tracking_email_id': self.id,
            })

    @api.multi
    def smtp_error(self, mail_server, smtp_server, exception):
        self.sudo().write({
            'error_smtp_server': tools.ustr(smtp_server),
            'error_type': exception.__class__.__name__,
            'error_description': tools.ustr(exception),
            'state': 'error',
        })
        return True

    @api.multi
    def tracking_img_add(self, email):
        self.ensure_one()
        tracking_url = self._get_mail_tracking_img()
        if tracking_url:
            body = tools.append_content_to_html(
                email.get('body', ''), tracking_url, plaintext=False,
                container_tag='div')
            email['body'] = body
        return email

    def _message_partners_check(self, message, message_id):
        mail_message = self.mail_message_id
        partners = mail_message.notified_partner_ids | mail_message.partner_ids
        if (self.partner_id and self.partner_id not in partners):
            # If mail_message haven't tracking partner, then
            # add it in order to see his trackking status in chatter
            if mail_message.subtype_id:
                mail_message.sudo().write({
                    'notified_partner_ids': [(4, self.partner_id.id)],
                })
            else:
                mail_message.sudo().write({
                    'partner_ids': [(4, self.partner_id.id)],
                })
        return True

    @api.multi
    def _tracking_sent_prepare(self, mail_server, smtp_server, message,
                               message_id):
        self.ensure_one()
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        self._message_partners_check(message, message_id)
        self.sudo().write({'state': 'sent'})
        return {
            'recipient': message['To'],
            'timestamp': '%.6f' % ts,
            'time': fields.Datetime.to_string(dt),
            'tracking_email_id': self.id,
            'event_type': 'sent',
            'smtp_server': smtp_server,
        }

    def _event_prepare(self, event_type, metadata):
        self.ensure_one()
        m_event = self.env['mail.tracking.event']
        method = getattr(m_event, 'process_' + event_type, None)
        if method and hasattr(method, '__call__'):
            return method(self, metadata)
        else:
            _logger.info('Unknown event type: %s' % event_type)
        return False

    @api.multi
    def event_process(self, event_type, metadata):
        event_ids = self.env['mail.tracking.event']
        for tracking_email in self:
            vals = tracking_email._event_prepare(event_type, metadata)
            if vals:
                event_ids += event_ids.sudo().create(vals)
        return event_ids
