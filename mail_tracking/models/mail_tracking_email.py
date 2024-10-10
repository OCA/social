# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
import urlparse
import time
import re
from datetime import datetime

from openerp import models, api, fields, tools
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)

EVENT_OPEN_DELTA = 10  # seconds
EVENT_CLICK_DELTA = 5  # seconds


class MailTrackingEmail(models.Model):
    _name = "mail.tracking.email"
    _order = 'time desc'
    _rec_name = 'display_name'
    _description = 'MailTracking email'

    name = fields.Char(string="Subject", readonly=True, index=True)
    display_name = fields.Char(
        string="Display name", readonly=True, store=True,
        compute="_compute_display_name")
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
    recipient_address = fields.Char(
        string='Recipient email address', readonly=True, store=True,
        compute='_compute_recipient_address')
    sender = fields.Char(string='Sender email', readonly=True)
    state = fields.Selection([
        ('error', 'Error'),
        ('deferred', 'Deferred'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
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
             " * The 'Opened' status indicates that message was opened or "
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

    @api.model
    def tracking_ids_recalculate(self, model, email_field, tracking_field,
                                 email, new_tracking=None):
        objects = self.env[model].search([
            (email_field, '=ilike', email),
        ])
        for obj in objects:
            trackings = obj[tracking_field]
            if new_tracking:
                trackings |= new_tracking
            trackings = trackings._email_score_tracking_filter()
            if set(obj[tracking_field].ids) != set(trackings.ids):
                if trackings:
                    obj.write({
                        tracking_field: [(6, False, trackings.ids)]
                    })
                else:
                    obj.write({
                        tracking_field: [(5, False, False)]
                    })
        return objects

    @api.model
    def _tracking_ids_to_write(self, email):
        trackings = self.env['mail.tracking.email'].search([
            ('recipient_address', '=ilike', email)
        ])
        trackings = trackings._email_score_tracking_filter()
        if trackings:
            return [(6, False, trackings.ids)]
        else:
            return [(5, False, False)]

    @api.multi
    def _email_score_tracking_filter(self):
        """Default email score filter for tracking emails"""
        # Consider only last 10 tracking emails
        return self.sorted(key=lambda r: r.time, reverse=True)[:10]

    @api.model
    def email_score_from_email(self, email):
        trackings = self.env['mail.tracking.email'].search([
            ('recipient_address', '=ilike', email)
        ])
        return trackings.email_score()

    @api.multi
    def email_score(self):
        """Default email score algorimth"""
        score = 50.0
        trackings = self._email_score_tracking_filter()
        for tracking in trackings:
            if tracking.state in ('error',):
                score -= 50.0
            elif tracking.state in ('rejected', 'spam', 'bounced'):
                score -= 25.0
            elif tracking.state in ('soft-bounced', 'unsub'):
                score -= 10.0
            elif tracking.state in ('delivered',):
                score += 5.0
            elif tracking.state in ('opened',):
                score += 10.0
        if score > 100.0:
            score = 100.0
        return score

    @api.multi
    @api.depends('recipient')
    def _compute_recipient_address(self):
        for email in self:
            matches = re.search(r'<(.*@.*)>', email.recipient)
            if matches:
                email.recipient_address = matches.group(1)
            else:
                email.recipient_address = email.recipient

    @api.multi
    @api.depends('name', 'recipient')
    def _compute_display_name(self):
        for email in self:
            parts = [email.name or '']
            if email.recipient:
                parts.append(email.recipient)
            email.display_name = ' - '.join(parts)

    @api.multi
    @api.depends('time')
    def _compute_date(self):
        for email in self:
            email.date = fields.Date.to_string(
                fields.Date.from_string(email.time))

    @api.model
    def create(self, vals):
        tracking = super(MailTrackingEmail, self).create(vals)
        self.tracking_ids_recalculate(
            'res.partner', 'email', 'tracking_email_ids',
            tracking.recipient_address, new_tracking=tracking)
        return tracking

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
        partners = (
            mail_message.needaction_partner_ids | mail_message.partner_ids)
        if (self.partner_id and self.partner_id not in partners):
            # If mail_message haven't tracking partner, then
            # add it in order to see his tracking status in chatter
            if mail_message.subtype_id:
                mail_message.sudo().write({
                    'needaction_partner_ids': [(4, self.partner_id.id)],
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
        else:  # pragma: no cover
            _logger.info('Unknown event type: %s' % event_type)
        return False

    def _concurrent_events(self, event_type, metadata):
        m_event = self.env['mail.tracking.event']
        self.ensure_one()
        concurrent_event_ids = False
        if event_type in {'open', 'click'}:
            ts = metadata.get('timestamp', time.time())
            delta = EVENT_OPEN_DELTA if event_type == 'open' \
                else EVENT_CLICK_DELTA
            domain = [
                ('timestamp', '>=', ts - delta),
                ('timestamp', '<=', ts + delta),
                ('tracking_email_id', '=', self.id),
                ('event_type', '=', event_type),
            ]
            if event_type == 'click':
                domain.append(('url', '=', metadata.get('url', False)))
            concurrent_event_ids = m_event.search(domain)
        return concurrent_event_ids

    @api.multi
    def event_create(self, event_type, metadata):
        event_ids = self.env['mail.tracking.event']
        for tracking_email in self:
            other_ids = tracking_email._concurrent_events(event_type, metadata)
            if not other_ids:
                vals = tracking_email._event_prepare(event_type, metadata)
                if vals:
                    event_ids += event_ids.sudo().create(vals)
                partners = self.tracking_ids_recalculate(
                    'res.partner', 'email', 'tracking_email_ids',
                    tracking_email.recipient_address)
                if partners:
                    partners.email_score_calculate()
            else:
                _logger.debug("Concurrent event '%s' discarded", event_type)
        return event_ids

    @api.model
    def event_process(self, request, post, metadata, event_type=None):
        # Generic event process hook, inherit it and
        # - return 'OK' if processed
        # - return 'NONE' if this request is not for you
        # - return 'ERROR' if any error
        return 'NONE'  # pragma: no cover
