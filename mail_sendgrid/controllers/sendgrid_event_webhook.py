# -*- coding: utf-8 -*-
# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import http
from odoo.addons.mail_tracking.controllers.main import \
    MailTrackingController, _env_get

_logger = logging.getLogger(__name__)


class SendgridTrackingController(MailTrackingController):
    """Sendgrid is posting JSON so we must define a new route for tracking."""
    @http.route('/mail/tracking/sendgrid/<string:db>',
                type='json', auth='none', csrf=False)
    def mail_tracking_sendgrid(self, db, **kw):
        try:
            _env_get(db, self._tracking_event, None, None, **kw)
            return {'status': 200}
        except Exception as e:
            _logger.error(e.message, exc_info=True)
            return {'status': 400}
