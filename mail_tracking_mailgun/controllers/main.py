# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import logging
from datetime import datetime, timedelta

from werkzeug.exceptions import NotAcceptable

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request, route

from ...mail_tracking.controllers import main
from ...web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)


class MailTrackingController(main.MailTrackingController):
    def _mail_tracking_mailgun_webhook_verify(self, timestamp, token, signature):
        """Avoid mailgun webhook attacks.

        See https://documentation.mailgun.com/en/latest/user_manual.html#securing-webhooks
        """  # noqa: E501
        # Request cannot be old
        processing_time = datetime.utcnow() - datetime.utcfromtimestamp(int(timestamp))
        if not timedelta() < processing_time < timedelta(minutes=10):
            raise ValidationError(_("Request is too old"))
        # Avoid replay attacks
        try:
            processed_tokens = (
                request.env.registry._mail_tracking_mailgun_processed_tokens
            )
        except AttributeError:
            processed_tokens = (
                request.env.registry._mail_tracking_mailgun_processed_tokens
            ) = set()
        if token in processed_tokens:
            raise ValidationError(_("Request was already processed"))
        processed_tokens.add(token)
        params = request.env["mail.tracking.email"]._mailgun_values()
        # Assert signature
        if not params.webhook_signing_key:
            _logger.warning(
                "Skipping webhook payload verification. "
                "Set `mailgun.webhook_signing_key` config parameter to enable"
            )
            return
        hmac_digest = hmac.new(
            key=params.webhook_signing_key.encode(),
            msg=("{}{}".format(timestamp, token)).encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(str(signature), str(hmac_digest)):
            raise ValidationError(_("Wrong signature"))

    @route(["/mail/tracking/mailgun/all"], auth="none", type="json", csrf=False)
    def mail_tracking_mailgun_webhook(self):
        """Process webhooks from Mailgun."""
        ensure_db()
        # Verify and return 406 in case of failure, to avoid retries
        # See https://documentation.mailgun.com/en/latest/user_manual.html#routes
        try:
            self._mail_tracking_mailgun_webhook_verify(
                **request.jsonrequest["signature"]
            )
        except ValidationError as error:
            raise NotAcceptable from error
        # v13: Under certain circumstances setting the bounce to hard faild partner
        # leads to a triggering of the property_pricelist recomputation. We need to set
        # company, user and uid for the query build to work correctly:
        # https://github.com
        # /odoo/odoo/blob/13.0/odoo/addons/base/models/ir_property.py#L240
        #
        # The result is an inderect error that impedes the correct bounce flagging and
        # the event record creation:
        #
        # > ERROR prod odoo.sql_db: bad query:
        # >
        # > SELECT substr(p.res_id, 13)::integer, r.id
        # > FROM ir_property p
        # > LEFT JOIN product_pricelist r ON substr(p.value_reference, 19)::integer=r.id
        # > WHERE p.fields_id=2440
        # >     AND (p.company_id=false OR p.company_id IS NULL)
        # >     AND (p.res_id IN ('res.partner,45621') OR p.res_id IS NULL)
        # > ORDER BY p.company_id NULLS FIRST
        # >
        # > ERROR: operator does not exist: integer = boolean
        # > LINE 6:                     AND (p.company_id=false OR p.company_id ...
        #
        # As far as we could research, this doesn't happen in >v14. So this nasty glitch
        # only needs a fix for this version.
        request.env.user = request.env["res.users"].browse(1)
        request.env.company = request.env["res.company"].search([], limit=1)
        request.env.uid = 1
        # Process event
        request.env["mail.tracking.email"].sudo()._mailgun_event_process(
            request.jsonrequest["event-data"], self._request_metadata(),
        )
