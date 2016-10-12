# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __openerp__.py
#
##############################################################################
import logging

from openerp import http, fields
from openerp.http import request
from werkzeug.useragents import UserAgent


STATUS_OK = 200

_logger = logging.getLogger(__name__)


class EventWebhook(http.Controller):
    """ Add SendGrid related fields so that they dispatch in all
    subclasses of mail.message object
    """

    # Map Sendgrid Events to mail_tracking event_type
    event_mapping = {
        # 'processed': 'sent', - not used
        'dropped': 'reject',
        'bounce': 'hard_bounce',
        'deferred': 'deferral',
        'delivered': 'delivered',
        'open': 'open',
        'click': 'click',
        'spamreport': 'spam',
        'unsubscribe': 'unsub',
        'group_unsubscribe': 'unsub',
    }

    @http.route('/sendgrid/events', type='json', auth='public', methods=[
        'POST'])
    def handler_sendgrid(self):
        message_data = request.jsonrequest
        _logger.info("SENDGRID Webhook received: %s" % str(message_data))
        if message_data and isinstance(message_data, list):
            message_data.sort(key=lambda m: m.get('timestamp'))
            for notification in message_data:
                event = notification.get('event')
                recipient = notification.get('email')
                message_id = notification.get('odoo_id')
                t_email = request.env['mail.tracking.email'].sudo().search([
                    ('mail_id.message_id', '=', message_id),
                    ('recipient', '=ilike', recipient)
                ], limit=1)
                if not t_email:
                    _logger.error("Sendgrid e-mail not found: %s" % message_id)
                    continue

                t_vals = {
                    'recipient': recipient,
                    'timestamp': notification.get('timestamp'),
                    'time': fields.Datetime.now(),
                    'tracking_email_id': t_email.id,
                    'ip': notification.get('ip'),
                    'smtp_server': notification.get('smtp-id'),
                    'url': notification.get('url')
                }
                if notification.get('useragent'):
                    user_agent = UserAgent(notification.get('useragent'))
                    t_vals.update({
                        'user_agent': user_agent.string,
                        'os_family': user_agent.platform,
                        'ua_family': user_agent.browser,
                        'mobile': user_agent.platform in [
                            'android', 'iphone', 'ipad']
                    })
                m_vals = {}
                event_type = self.event_mapping.get(event)
                if not event_type:
                    # Skip unmapped events
                    continue

                if event == 'dropped':
                    m_vals.update({
                        'error_description': notification.get('reason'),
                    })
                    t_vals['error_type'] = notification.get('reason')
                elif event == 'bounce':
                    bounce_type = notification.get('type')
                    if bounce_type == 'blocked':
                        event_type = 'spam'
                    t_vals.update({
                        'error_type': notification.get('type'),
                        'error_description': notification.get('reason'),
                    })
                    m_vals.update({
                        'error_type': notification.get('status'),
                        'bounce_type': bounce_type,
                        'bounce_description': notification.get('reason'),
                    })
                elif event == 'deferred':
                    m_vals.update({
                        'error_smtp_server': notification.get('response'),
                    })

                # Create tracking event
                t_email.event_create(event_type, t_vals)
                # Write email tracking modifications
                if m_vals:
                    t_email.write(m_vals)

            return {'status': 200}

        else:
            return {'status': 400, 'message': 'wrong request'}
