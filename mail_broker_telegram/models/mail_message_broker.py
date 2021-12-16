import base64
import logging
import traceback
from io import BytesIO, StringIO

from odoo import _, models
from odoo.tools import html2plaintext

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


class MailMessageBroker(models.Model):
    _inherit = "mail.message.broker"

    def _send_telegram(
        self, auto_commit=False, raise_exception=False, parse_mode=False
    ):
        message = False
        try:
            bot = self.channel_id.broker_id._get_telegram_bot()
            chat = bot.get_chat(self.channel_id.token)
            if self.body:
                message = chat.send_message(
                    html2plaintext(self.body), parse_mode=parse_mode
                )
            for attachment in self.attachment_ids:
                if attachment.mimetype.split("/")[0] == "image":
                    new_message = chat.send_photo(
                        BytesIO(base64.b64decode(attachment.datas))
                    )
                else:
                    new_message = chat.send_document(
                        BytesIO(base64.b64decode(attachment.datas)),
                        filename=attachment.name,
                    )
                if not message:
                    message = new_message
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    _("Unable to send the telegram message"), exc
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
                    "message_id": message.message_id,
                    "failure_reason": False,
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self._cr.commit()
