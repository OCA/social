# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug
from psycopg2 import OperationalError
from odoo import api, http, registry, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

BLANK = b'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='


def _env_get(db, callback, tracking_id, event_type, **kw):
    res = 'NOT FOUND'
    reg = False
    current = http.request.db and db == http.request.db
    env = current and http.request.env
    if not env:
        with api.Environment.manage():
            try:
                reg = registry(db)
            except OperationalError:
                _logger.warning("Selected BD '%s' not found", db)
            except Exception:  # pragma: no cover
                _logger.warning("Selected BD '%s' connection error", db)
            if reg:
                _logger.info("New environment for database '%s'", db)
                with reg.cursor() as new_cr:
                    new_env = api.Environment(new_cr, SUPERUSER_ID, {})
                    res = callback(new_env, tracking_id, event_type, **kw)
                    new_env.cr.commit()
    else:
        # make sudo when reusing environment
        env = env(user=SUPERUSER_ID)
        res = callback(env, tracking_id, event_type, **kw)
    return res


class MailTrackingController(http.Controller):

    def _request_metadata(self):
        request = http.request.httprequest
        return {
            'ip': request.remote_addr or False,
            'user_agent': request.user_agent or False,
            'os_family': request.user_agent.platform or False,
            'ua_family': request.user_agent.browser or False,
        }

    def _tracking_open(self, env, tracking_id, event_type, **kw):
        tracking_email = env['mail.tracking.email'].search([
            ('id', '=', tracking_id),
        ])
        if tracking_email:
            metadata = self._request_metadata()
            tracking_email.event_create('open', metadata)
        else:
            _logger.warning(
                "MailTracking email '%s' not found", tracking_id)

    def _tracking_event(self, env, tracking_id, event_type, **kw):
        metadata = self._request_metadata()
        return env['mail.tracking.email'].event_process(
            http.request, kw, metadata, event_type=event_type)

    @http.route('/mail/tracking/all/<string:db>',
                type='http', auth='none', csrf=False)
    def mail_tracking_all(self, db, **kw):
        return _env_get(db, self._tracking_event, None, None, **kw)

    @http.route('/mail/tracking/event/<string:db>/<string:event_type>',
                type='http', auth='none', csrf=False)
    def mail_tracking_event(self, db, event_type, **kw):
        return _env_get(db, self._tracking_event, None, event_type, **kw)

    @http.route('/mail/tracking/open/<string:db>'
                '/<int:tracking_email_id>/blank.gif',
                type='http', auth='none')
    def mail_tracking_open(self, db, tracking_email_id, **kw):
        _env_get(db, self._tracking_open, tracking_email_id, None, **kw)

        # Always return GIF blank image
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = BLANK
        return response
