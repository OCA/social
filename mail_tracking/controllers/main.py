# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug
from psycopg2 import OperationalError
from openerp import api, http, registry, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

BLANK = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='


def _env_get(db):
    reg = False
    try:
        reg = registry(db)
    except OperationalError:
        _logger.warning("Selected BD '%s' not found", db)
    except:  # pragma: no cover
        _logger.warning("Selected BD '%s' connection error", db)
    if reg:
        return api.Environment(reg.cursor(), SUPERUSER_ID, {})
    return False


class MailTrackingController(http.Controller):

    def _request_metadata(self):
        request = http.request.httprequest
        return {
            'ip': request.remote_addr or False,
            'user_agent': request.user_agent or False,
            'os_family': request.user_agent.platform or False,
            'ua_family': request.user_agent.browser or False,
        }

    @http.route('/mail/tracking/all/<string:db>',
                type='http', auth='none')
    def mail_tracking_all(self, db, **kw):
        env = _env_get(db)
        if not env:
            return 'NOT FOUND'
        metadata = self._request_metadata()
        response = env['mail.tracking.email'].event_process(
            http.request, kw, metadata)
        env.cr.commit()
        env.cr.close()
        return response

    @http.route('/mail/tracking/event/<string:db>/<string:event_type>',
                type='http', auth='none')
    def mail_tracking_event(self, db, event_type, **kw):
        env = _env_get(db)
        if not env:
            return 'NOT FOUND'
        metadata = self._request_metadata()
        response = env['mail.tracking.email'].event_process(
            http.request, kw, metadata, event_type=event_type)
        env.cr.commit()
        env.cr.close()
        return response

    @http.route('/mail/tracking/open/<string:db>'
                '/<int:tracking_email_id>/blank.gif',
                type='http', auth='none')
    def mail_tracking_open(self, db, tracking_email_id, **kw):
        env = _env_get(db)
        if env:
            tracking_email = env['mail.tracking.email'].search([
                ('id', '=', tracking_email_id),
            ])
            if tracking_email:
                metadata = self._request_metadata()
                tracking_email.event_create('open', metadata)
            else:
                _logger.warning(
                    "MailTracking email '%s' not found", tracking_email_id)
            env.cr.commit()
            env.cr.close()

        # Always return GIF blank image
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = BLANK.decode('base64')
        return response
