# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from datetime import datetime

from werkzeug.useragents import UserAgent

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MailTrackingEmail(models.Model):
    """ Count the user clicks on links inside e-mails sent.
        Add tracking methods to process Sendgrid Notifications
    """
    _inherit = 'mail.tracking.email'

    click_count = fields.Integer(
        compute='_compute_clicks', store=True, readonly=True)

    @api.depends('tracking_event_ids')
    def _compute_clicks(self):
        for mail in self:
            mail.click_count = self.env['mail.tracking.event'].search_count([
                ('event_type', '=', 'click'),
                ('tracking_email_id', '=', mail.id)
            ])

    @property
    def _sendgrid_mandatory_fields(self):
        return ('event', 'timestamp', 'odoo_id', 'odoo_db')

    @property
    def _sendgrid_event_type_mapping(self):
        return {
            # Sendgrid event type: tracking event type
            'bounce': 'hard_bounce',
            'click': 'click',
            'deferred': 'deferral',
            'delivered': 'delivered',
            'dropped': 'reject',
            'group_unsubscribe': 'unsub',
            'open': 'open',
            'processed': 'sent',
            'spamreport': 'spam',
            'unsubscribe': 'unsub',
        }

    def _sendgrid_event_type_verify(self, event):
        event = event or {}
        sendgrid_event_type = event.get('event')
        if sendgrid_event_type not in self._sendgrid_event_type_mapping:
            _logger.error("Sendgrid: event type '%s' not supported",
                          sendgrid_event_type)
            return False
        # OK, event type is valid
        return True

    def _sendgrid_db_verify(self, event):
        event = event or {}
        odoo_db = event.get('odoo_db')
        current_db = self.env.cr.dbname
        if odoo_db != current_db:
            _logger.error("Sendgrid: Database '%s' is not the current "
                          "database",
                          odoo_db)
            return False
        # OK, DB is current
        return True

    def _sendgrid_metadata(self, sendgrid_event_type, event, metadata):
        # Get sendgrid timestamp when found
        ts = event.get('timestamp')
        try:
            ts = float(ts)
        except ValueError:
            ts = False
        if ts:
            dt = datetime.utcfromtimestamp(ts)
            metadata.update({
                'timestamp': ts,
                'time': fields.Datetime.to_string(dt),
                'date': fields.Date.to_string(dt),
            })
        # Common field mapping (sendgrid_field: odoo_field)
        mapping = {
            'email': 'recipient',
            'ip': 'ip',
            'url': 'url',
        }
        for k, v in mapping.iteritems():
            if event.get(k, False):
                metadata[v] = event[k]
        # Special field mapping
        if event.get('useragent'):
            user_agent = UserAgent(event['useragent'])
            metadata.update({
                'user_agent': user_agent.string,
                'os_family': user_agent.platform,
                'ua_family': user_agent.browser,
                'mobile': user_agent.platform in [
                    'android', 'iphone', 'ipad']
            })
        # Mapping for special events
        if sendgrid_event_type == 'bounce':
            metadata.update({
                'error_type': event.get('type', False),
                'bounce_type': event.get('type', False),
                'error_description': event.get('reason', False),
                'bounce_description': event.get('reason', False),
                'error_details': event.get('status', False),
            })
        elif sendgrid_event_type == 'dropped':
            metadata.update({
                'error_type': event.get('reason', False),
            })
        return metadata

    def _sendgrid_tracking_get(self, event):
        tracking = False
        message_id = event.get('odoo_id', False)
        if message_id:
            tracking = self.search([
                ('mail_id.message_id', '=', message_id),
                ('recipient', '=ilike', event.get('email'))], limit=1)
        return tracking

    def _event_is_from_sendgrid(self, event):
        event = event or {}
        return all([k in event for k in self._sendgrid_mandatory_fields])

    @api.model
    def event_process(self, request, post, metadata, event_type=None):
        res = super(MailTrackingEmail, self).event_process(
            request, post, metadata, event_type=event_type)
        is_json = hasattr(request, 'jsonrequest') and isinstance(
            request.jsonrequest, list)
        if res == 'NONE' and is_json:
            for event in request.jsonrequest:
                if self._event_is_from_sendgrid(event):
                    if not self._sendgrid_event_type_verify(event):
                        res = 'ERROR: Event type not supported'
                    elif not self._sendgrid_db_verify(event):
                        res = 'ERROR: Invalid DB'
                    else:
                        res = 'OK'
                if res == 'OK':
                    sendgrid_event_type = event.get('event')
                    mapped_event_type = self._sendgrid_event_type_mapping.get(
                        sendgrid_event_type) or event_type
                    if not mapped_event_type:
                        res = 'ERROR: Bad event'
                    tracking = self._sendgrid_tracking_get(event)
                    if tracking:
                        # Complete metadata with sendgrid event info
                        metadata = self._sendgrid_metadata(
                            sendgrid_event_type, event, metadata)
                        # Create event
                        tracking.event_create(mapped_event_type, metadata)
                    else:
                        res = 'ERROR: Tracking not found'
                if res != 'NONE':
                    if event_type:
                        _logger.info(
                            "sendgrid: event '%s' process '%s'",
                            event_type, res)
                    else:
                        _logger.info("sendgrid: event process '%s'", res)
        return res
