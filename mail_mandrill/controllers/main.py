# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

import json
from hashlib import sha1
import hmac
import logging
from psycopg2 import OperationalError

import openerp
from openerp import api, http, SUPERUSER_ID, tools
from openerp.http import request

_logger = logging.getLogger(__name__)


class MailController(http.Controller):

    def _mandrill_validation(self, **kw):
        """
            Validate Mandrill POST reques using
            https://mandrill.zendesk.com/hc/en-us/articles/
205583257-Authenticating-webhook-requests
        """
        headers = request.httprequest.headers
        signature = headers.get('X-Mandrill-Signature', False)
        key = tools.config.options.get('mandrill_webhook_key', False)
        if not key:
            _logger.info("No Mandrill validation key configured. "
                         "Please add 'mandrill_webhook_key' to [options] "
                         "section in odoo configuration file to enable "
                         "Mandrill authentication webhoook requests. "
                         "More info at: "
                         "https://mandrill.zendesk.com/hc/en-us/articles/"
                         "205583257-Authenticating-webhook-requests")
            return True
        if not signature:
            return False
        url = tools.config.options.get('mandrill_webhook_url', False)
        if not url:
            url = request.httprequest.url_root.rstrip('/') + '/mandrill/event'
        data = url
        kw_keys = kw.keys()
        if kw_keys:
            kw_keys.sort()
            for kw_key in kw_keys:
                data += kw_key + kw.get(kw_key)
        hashed = hmac.new(key, data, sha1)
        hash_text = hashed.digest().encode("base64").rstrip('\n')
        if hash_text == signature:
            return True
        _logger.info("HASH[%s] != SIGNATURE[%s]" % (hash_text, signature))
        return False

    def _event_process(self, event):
        message_id = event.get('_id')
        event_type = event.get('event')
        message = event.get('msg')
        if not (message_id and event_type and message):
            return False

        info = "%s event for Message ID '%s'" % (event_type, message_id)
        metadata = message.get('metadata')
        db = None
        if metadata:
            db = metadata.get('odoo_db', None)

        # Check database selected by mandrill event
        if not db:
            _logger.info('%s: No DB selected', info)
            return False
        try:
            registry = openerp.registry(db)
        except OperationalError:
            _logger.info("%s: Selected BD '%s' not found", info, db)
            return False
        except:
            _logger.info("%s: Selected BD '%s' connection error", info, db)
            return False

        # Database has been selected, process event
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            res = env['mail.mandrill.message'].process(
                message_id, event_type, event)
        if res:
            _logger.info('%s: OK', info)
        else:
            _logger.info('%s: FAILED', info)
        return res

    @http.route('/mandrill/event', type='http', auth='none')
    def event(self, **kw):
        """
        End-point to receive Mandrill event
        Configuration in Mandrill app > Settings > Webhooks
            (https://mandrillapp.com/settings/webhooks)
        Add a webhook, selecting this type of events:
        - Message Is Sent
        - Message Is Bounced
        - Message Is Opened
        - Message Is Marked As Spam
        - Message Is Rejected
        - Message Is Delayed
        - Message Is Soft-Bounced
        - Message Is Clicked
        - Message Recipient Unsubscribes
        and setting this Post to URL:
            https://your_odoodomain.com/mandrill/event
        """
        if not self._mandrill_validation(**kw):
            _logger.info('Validation error, ignoring this request')
            return 'NO_AUTH'
        events = []
        try:
            events = json.loads(kw.get('mandrill_events', '[]'))
        except:
            pass
        if not events:
            return 'NO_EVENTS'
        res = []
        for event in events:
            res.append(self._event_process(event))
        msg = 'ALL_EVENTS_FAILED'
        if all(res):
            msg = 'OK'
        elif any(res):
            msg = 'SOME_EVENTS_FAILED'
        return msg
