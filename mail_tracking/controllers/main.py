# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging
from contextlib import contextmanager

import werkzeug

import odoo
from odoo import SUPERUSER_ID, api, http

from odoo.addons.mail.controllers.discuss import DiscussController
from odoo.addons.mail.controllers.mail import MailController

_logger = logging.getLogger(__name__)

BLANK = "R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="


@contextmanager
def db_env(dbname):
    if not http.db_filter([dbname]):
        raise werkzeug.exceptions.BadRequest()
    cr = None
    if dbname == http.request.db:
        cr = http.request.cr
    if not cr:
        cr = odoo.sql_db.db_connect(dbname).cursor()
    yield api.Environment(cr, SUPERUSER_ID, {})


class MailTrackingController(MailController, DiscussController):
    def _request_metadata(self):
        """Prepare remote info metadata"""
        request = http.request.httprequest
        return {
            "ip": request.remote_addr or False,
            "user_agent": request.user_agent or False,
            "os_family": request.user_agent.platform or False,
            "ua_family": request.user_agent.browser or False,
        }

    @http.route(
        [
            "/mail/tracking/all/<string:db>",
            "/mail/tracking/event/<string:db>/<string:event_type>",
        ],
        type="http",
        auth="none",
        csrf=False,
    )
    def mail_tracking_event(self, db, event_type=None, **kw):
        """Route used by external mail service"""
        metadata = self._request_metadata()
        res = None
        with db_env(db) as env:
            try:
                res = env["mail.tracking.email"].event_process(
                    http.request, kw, metadata, event_type=event_type
                )
            except Exception as e:
                _logger.warning(e)
        if not res or res == "NOT FOUND":
            return werkzeug.exceptions.NotAcceptable()
        return res

    @http.route(
        [
            "/mail/tracking/open/<string:db>" "/<int:tracking_email_id>/blank.gif",
            "/mail/tracking/open/<string:db>"
            "/<int:tracking_email_id>/<string:token>/blank.gif",
        ],
        type="http",
        auth="none",
        methods=["GET"],
    )
    def mail_tracking_open(self, db, tracking_email_id, token=False, **kw):
        """Route used to track mail openned (With & Without Token)"""
        metadata = self._request_metadata()
        with db_env(db) as env:
            try:
                tracking_email = env["mail.tracking.email"].search(
                    [("id", "=", tracking_email_id), ("token", "=", token)]
                )
                if not tracking_email:
                    _logger.warning(
                        "MailTracking email '%s' not found", tracking_email_id
                    )
                elif tracking_email.state in ("sent", "delivered"):
                    tracking_email.event_create("open", metadata)
            except Exception as e:
                _logger.warning(e)

        # Always return GIF blank image
        response = werkzeug.wrappers.Response()
        response.mimetype = "image/gif"
        response.data = base64.b64decode(BLANK)
        return response

    @http.route()
    def mail_init_messaging(self):
        """Route used to initial values of Discuss app"""
        values = super().mail_init_messaging()
        values.update(
            {"failed_counter": http.request.env["mail.message"].get_failed_count()}
        )
        return values

    @http.route("/mail/failed/messages", methods=["POST"], type="json", auth="user")
    def discuss_failed_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return http.request.env["mail.message"]._message_fetch(
            domain=[("is_failed_message", "=", True)],
            max_id=max_id,
            min_id=min_id,
            limit=limit,
        )
