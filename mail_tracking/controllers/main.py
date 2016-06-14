# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug
from psycopg2 import OperationalError
from openerp import api, http, registry, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

BLANK = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='


class MailTrackingController(http.Controller):

    def _request_metadata(self):
        request = http.request.httprequest
        return {
            'ip': request.remote_addr,
            'user_agent': request.user_agent,
            'os_family': request.user_agent.platform,
            'ua_family': request.user_agent.browser,
        }

    @http.route('/mail/tracking/open/<string:db>'
                '/<int:tracking_email_id>/blank.gif',
                type='http', auth='none')
    def mail_tracking_open(self, db, tracking_email_id, **kw):
        reg = False
        try:
            reg = registry(db)
        except OperationalError:
            _logger.warning("Selected BD '%s' not found", db)
        except:
            _logger.warning("Selected BD '%s' connection error", db)
        if reg:
            with reg.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                tracking_email = env['mail.tracking.email'].search([
                    ('id', '=', tracking_email_id),
                ])
                if tracking_email:
                    metadata = self._request_metadata()
                    tracking_email.event_process('open', metadata)
                else:
                    _logger.warning(
                        "MailTracking email '%s' not found", tracking_email_id)

        # Always return GIF blank image
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = BLANK.decode('base64')
        return response
