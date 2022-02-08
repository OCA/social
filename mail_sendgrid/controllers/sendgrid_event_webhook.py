# Copyright 2016-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo import http

from odoo.addons.mail_tracking.controllers.main import MailTrackingController, db_env

_logger = logging.getLogger(__name__)


class SendgridTrackingController(MailTrackingController):
    """Sendgrid is posting JSON so we must define a new route for tracking."""

    @http.route(
        "/mail/tracking/sendgrid/<string:db>", type="json", auth="none", csrf=False
    )
    def mail_tracking_sendgrid(self, db, **kw):
        metadata = self._request_metadata()
        with db_env(db) as env:
            try:
                env["mail.tracking.email"].event_process(http.request, kw, metadata)
                return {"status": 200}
            except Exception as e:
                _logger.error(str(e), exc_info=True)
                return {"status": 400}
