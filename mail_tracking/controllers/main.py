# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug
from psycopg2 import OperationalError
from odoo import api, http, registry, SUPERUSER_ID
from odoo.addons.mail.controllers.main import MailController
from odoo.http import request
import logging
import base64
_logger = logging.getLogger(__name__)

BLANK = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='


# Helper class to invoke "_tracking_*" methods
class EnvironmentDB:
    def __init__(self, db):
        self.db = db
        self.__is_new = False
        self._env = False

    def __enter__(self):
        reg = False
        current = http.request.db and self.db == http.request.db
        self._env = current and http.request.env
        if not self._env:
            with api.Environment.manage():
                try:
                    reg = registry(self.db)
                except OperationalError:
                    _logger.warning("Selected BD '%s' not found", self.db)
                except Exception:  # pragma: no cover
                    _logger.warning(
                        "Selected BD '%s' connection error", self.db)
                if reg:
                    self.__is_new = True
                    _logger.info("New environment for database '%s'", self.db)
                    with reg.cursor() as new_cr:
                        self._env = api.Environment(new_cr, SUPERUSER_ID, {})
                        return self._env
        else:
            self._env = self._env(user=SUPERUSER_ID)
        return self._env

    def __exit__(self, type, value, traceback):
        if self.__is_new:
            self._env.cr.commit()


class MailTrackingController(MailController):

    # Prepare remote info metadata
    def _request_metadata(self):
        request = http.request.httprequest
        return {
            'ip': request.remote_addr or False,
            'user_agent': request.user_agent or False,
            'os_family': request.user_agent.platform or False,
            'ua_family': request.user_agent.browser or False,
        }

    # Tracking Open (Compatible with tracking without generated token)
    def _tracking_open(self, env, tracking_id, token, **kw):
        tracking_email = env['mail.tracking.email'].search([
            ('id', '=', tracking_id),
            ('state', 'in', ['sent', 'delivered']),
            ('token', '=', token),
        ])
        if tracking_email:
            metadata = self._request_metadata()
            tracking_email.event_create('open', metadata)
        else:
            _logger.warning(
                "MailTracking email '%s' not found", tracking_id)

    # Tracking Event without token
    def _tracking_event(self, env, event_type, **kw):
        metadata = self._request_metadata()
        return env['mail.tracking.email'].event_process(
            http.request, kw, metadata, event_type=event_type)

    # Route used by external mail service
    @http.route('/mail/tracking/all/<string:db>',
                type='http', auth='none', csrf=False)
    def mail_tracking_all(self, db, **kw):
        with EnvironmentDB(db) as env:
            return self._tracking_event(env, None) if env else 'NOT FOUND'

    # Route used by external mail service
    @http.route('/mail/tracking/event/<string:db>/<string:event_type>',
                type='http', auth='none', csrf=False)
    def mail_tracking_event(self, db, event_type, **kw):
        with EnvironmentDB(db) as env:
            return (self._tracking_event(env, event_type)
                    if env else 'NOT FOUND')

    # Route used to track mail openned (With & Without Token)
    @http.route(['/mail/tracking/open/<string:db>'
                 '/<int:tracking_email_id>/blank.gif',
                 '/mail/tracking/open/<string:db>'
                 '/<int:tracking_email_id>/<string:token>/blank.gif'],
                type='http', auth='none')
    def mail_tracking_open(self, db, tracking_email_id, token=False, **kw):
        with EnvironmentDB(db) as env:
            if env:
                self._tracking_open(env, tracking_email_id, token)

        # Always return GIF blank image
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = base64.b64decode(BLANK)
        return response

    # Route used to initial values of Discuss app
    @http.route()
    def mail_init_messaging(self):
        values = super().mail_init_messaging()
        values.update({
            'failed_counter': request.env['mail.message'].get_failed_count(),
        })
        return values
