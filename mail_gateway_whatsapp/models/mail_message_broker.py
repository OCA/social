# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import traceback
from io import StringIO

import requests

from odoo import _, models
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


class MailMessageBroker(models.Model):
    _inherit = "mail.message.broker"

    def _send_whatsapp_payload(self, body=False, media_id=False):
        if body:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.channel_id.token,
                "type": "text",
                "text": {"preview_url": False, "body": html2plaintext(body)},
            }
        if media_id:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.channel_id.token,
                "type": "image",
                "image": {"id": media_id},
            }

    def _send_whatsapp(
        self, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        message = False
        try:
            # TODO: Now only works for text. improve it...
            if self.body:
                response = requests.post(
                    "https://graph.facebook.com/v13.0/%s/messages"
                    % self.channel_id.broker_id.whatsapp_from_phone,
                    headers={
                        "Authorization": "Bearer %s" % self.channel_id.broker_id.token,
                    },
                    json=self._send_whatsapp_payload(body=self.body),
                )
                response.raise_for_status()
                message = response.json()
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    _("Unable to send the whatsapp message"), exc
                )
            else:
                _logger.warning(
                    "Issue sending message with id {}: {}".format(self.id, exc)
                )
                self.write({"state": "exception", "failure_reason": exc})
        if message:
            self.write(
                {
                    "state": "sent",
                    "message_id": message["messages"][0]["id"],
                    "failure_reason": False,
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self._cr.commit()
