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

from openerp import http
from openerp.addons.mail_tracking.controllers.main import \
    MailTrackingController, _env_get

_logger = logging.getLogger(__name__)


class SendgridTrackingController(MailTrackingController):
    """
    Sendgrid is posting JSON so we must define a new route for tracking.
    """
    @http.route('/mail/tracking/sendgrid/<string:db>',
                type='json', auth='none', csrf=False)
    def mail_tracking_sendgrid(self, db, **kw):
        try:
            _env_get(db, self._tracking_event, None, None, **kw)
            return {'status': 200}
        except:
            return {'status': 400}
