# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import base64
import logging
import mimetypes
import traceback
from io import BytesIO, StringIO

from odoo import _
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)

try:
    import telegram
    from lottie.exporters import exporters
    from lottie.importers import importers
except (ImportError, IOError) as err:
    _logger.debug(err)


class MailBrokerTelegramService(Component):
    _inherit = "mail.broker.base.service"
    _name = "mail.broker.telegram.service"
    _usage = "telegram"
    _description = "Telegram Broker services"

    def _get_telegram_bot(self, token=False):
        return telegram.Bot(token or self.collection.token)

    def _set_webhook(self):
        bot = self._get_telegram_bot()
        bot.setWebhook(
            url=self.collection.webhook_url,
            api_kwargs={"secret_token": self.collection.webhook_secret},
        )
        super()._set_webhook()

    def _remove_webhook(self):
        bot = self._get_telegram_bot()
        webhookinfo = bot.get_webhook_info()
        if webhookinfo.url:
            bot.delete_webhook(drop_pending_updates=False)
        super()._remove_webhook()

    def _verify_update(self, bot_data, kwargs):
        if not bot_data["webhook_secret"]:
            return True
        return (
            request.httprequest.headers.get("X-Telegram-Bot-Api-Secret-Token")
            == bot_data["webhook_secret"]
        )

    def _get_channel_vals(self, broker, token, update):
        result = super()._get_channel_vals(broker, token, update)
        names = []
        for name in [
            update.message.chat.first_name or False,
            update.message.chat.last_name or False,
            update.message.chat.description or False,
            update.message.chat.title or False,
        ]:
            if name:
                names.append(name)
        result["name"] = " ".join(names)
        return result

    def _preprocess_update(self, broker, update):
        for entity in update.message.entities:
            if not entity.offset == 0:
                continue
            if not entity.type == "bot_command":
                continue
            command = update.message.parse_entity(entity).split("/")[1]
            if hasattr(self, "_command_%s" % (command)):
                return getattr(self, "_command_%s" % (command))(broker, update)
        return False

    def _command_start(self, broker, update):
        if (
            not broker.has_new_channel_security
            or update.message.text == "/start %s" % broker.telegram_security_key
        ):
            return self._get_channel(broker, update.message.chat_id, update, True)
        return True

    def _receive_update(self, broker, update):
        telegram_update = telegram.Update.de_json(
            update, self._get_telegram_bot(token=broker.token)
        )
        if self._preprocess_update(broker, telegram_update):
            return
        chat = self._get_channel(
            broker, telegram_update.message.chat_id, telegram_update
        )
        if not chat:
            return
        return self._process_update(chat, telegram_update)

    def _telegram_sticker_input_options(self):
        return {}

    def _telegram_sticker_output_options(self):
        return {}

    def _get_telegram_attachment_name(self, attachment):
        if hasattr(attachment, "title"):
            if attachment.title:
                return attachment.title
        if hasattr(attachment, "file_name"):
            if attachment.file_name:
                return attachment.file_name
        if isinstance(attachment, telegram.Sticker):
            return attachment.set_name or attachment.emoji or "sticker"
        if isinstance(attachment, telegram.Contact):
            return attachment.first_name
        return attachment.file_id

    def _process_telegram_attachment(self, attachment):
        if isinstance(
            attachment,
            (
                telegram.Game,
                telegram.Invoice,
                telegram.Location,
                telegram.SuccessfulPayment,
                telegram.Venue,
            ),
        ):
            return
        if isinstance(attachment, telegram.Contact):
            data = attachment.vcard.encode("utf-8")
        else:
            data = bytes(attachment.get_file().download_as_bytearray())
        file_name = self._get_telegram_attachment_name(attachment)
        if isinstance(attachment, telegram.Sticker):
            suf = "tgs"
            for p in importers:
                if suf in p.extensions:
                    importer = p
                    break
            exporter = exporters.get("gif")
            inpt = BytesIO(data)
            an = importer.process(inpt, **self._telegram_sticker_input_options())
            output_options = self._telegram_sticker_output_options()
            fps = output_options.pop("fps", False)
            if fps:
                an.frame_rate = fps
            output = BytesIO()
            exporter.process(an, output, **output_options)
            data = output.getvalue()
        mimetype = guess_mimetype(data)
        return (
            "{}{}".format(file_name, mimetypes.guess_extension(mimetype)),
            base64.b64encode(data).decode("utf-8"),
            mimetype,
        )

    def _process_update(self, chat, update):
        chat.ensure_one()
        body = ""
        attachments = []
        if update.message.text_html:
            body = update.message.text_html
        if update.message.effective_attachment:
            effective_attachment = update.message.effective_attachment
            if isinstance(effective_attachment, list):
                current_attachment = effective_attachment[0]
                for attachment in effective_attachment[1:]:
                    if getattr(attachment, "file_size", 0) > getattr(
                        current_attachment, "file_size", 0
                    ):
                        current_attachment = attachment
                effective_attachment = current_attachment
            if isinstance(effective_attachment, telegram.Location):
                body += (
                    '<a target="_blank" href="https://www.google.com/'
                    'maps/search/?api=1&query=%s,%s">Location</a>'
                    % (
                        effective_attachment.latitude,
                        effective_attachment.longitude,
                    )
                )
            attachment_data = self._process_telegram_attachment(effective_attachment)
            if attachment_data:
                attachments.append(attachment_data)
        if len(body) > 0 or attachments:
            return chat.message_post_broker(
                body=body,
                broker_type="telegram",
                date=update.message.date.replace(tzinfo=None),
                message_id=update.message.message_id,
                subtype="mt_comment",
                attachments=attachments,
            )

    def _send(self, record, auto_commit=False, raise_exception=False, parse_mode=False):
        message = False
        try:
            bot = self._get_telegram_bot()
            chat = bot.get_chat(record.channel_id.token)
            if record.body:
                message = chat.send_message(
                    html2plaintext(record.body), parse_mode=parse_mode
                )
            for attachment in record.attachment_ids:
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
                    "Issue sending message with id {}: {}".format(record.id, exc)
                )
                record.write({"state": "exception", "failure_reason": exc})
        if message:
            record.write(
                {
                    "state": "sent",
                    "message_id": message.message_id,
                    "failure_reason": False,
                }
            )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()
