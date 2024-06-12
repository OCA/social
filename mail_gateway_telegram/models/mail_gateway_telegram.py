# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import mimetypes
import traceback
from io import BytesIO, StringIO

from odoo import _, models
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

try:
    import asyncio

    import telegram
    from lottie.exporters import exporters
    from lottie.importers import importers
except (ImportError, IOError) as err:
    _logger.debug(err)


class MailGatewayTelegramService(models.AbstractModel):
    _inherit = "mail.gateway.abstract"
    _name = "mail.gateway.telegram"
    _description = "Telegram Gateway services"

    def _get_telegram_bot(self, token=False):
        return telegram.Bot(token)

    def _set_webhook(self, gateway):
        bot = self._get_telegram_bot(gateway.token)
        asyncio.run(
            bot.setWebhook(
                url=gateway.webhook_url,
                api_kwargs={"secret_token": gateway.webhook_secret},
            )
        )
        return super()._set_webhook(gateway)

    async def _remove_webhook_telegram(self, gateway):
        bot = self._get_telegram_bot(gateway.token)
        await bot.initialize()
        webhookinfo = await bot.get_webhook_info()
        if webhookinfo.url:
            await bot.delete_webhook(drop_pending_updates=False)

    def _remove_webhook(self, gateway):
        asyncio.run(self._remove_webhook_telegram(gateway))
        return super()._remove_webhook(gateway)

    def _verify_update(self, bot_data, kwargs):
        if not bot_data["webhook_secret"]:
            return True
        return (
            request.httprequest.headers.get("X-Telegram-Bot-Api-Secret-Token")
            == bot_data["webhook_secret"]
        )

    def _get_channel_vals(self, gateway, token, update):
        result = super()._get_channel_vals(gateway, token, update)
        names = []
        for name in [
            update.message.chat.first_name or False,
            update.message.chat.last_name or False,
            update.message.chat.title or False,
        ]:
            if name:
                names.append(name)
        result["name"] = " ".join(names)
        result["anonymous_name"] = " ".join(names)
        return result

    def _preprocess_update(self, gateway, update):
        for entity in update.message.entities:
            if not entity.offset == 0:
                continue
            if not entity.type == "bot_command":
                continue
            command = update.message.parse_entity(entity).split("/")[1]
            if hasattr(self, "_command_%s" % (command)):
                return getattr(self, "_command_%s" % (command))(gateway, update)
        return False

    def _command_start(self, gateway, update):
        if (
            not gateway.has_new_channel_security
            or update.message.text == "/start %s" % gateway.telegram_security_key
        ):
            return self._get_channel(gateway, update.message.chat_id, update, True)
        return True

    def _receive_update(self, gateway, update):
        telegram_update = telegram.Update.de_json(
            update, self._get_telegram_bot(token=gateway.token)
        )
        if self._preprocess_update(gateway, telegram_update):
            return
        chat = self._get_channel(
            gateway, telegram_update.message.chat_id, telegram_update
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

    async def _process_telegram_attachment(self, attachment):
        if isinstance(attachment, tuple):
            attachment = attachment[-1]
            # That might happen with images, we will get the last one as it is the bigger one.
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
            file = await attachment.get_file()
            data = bytes(await file.download_as_bytearray())
        file_name = self._get_telegram_attachment_name(attachment)
        if isinstance(attachment, telegram.Sticker):
            _logger.debug("Processing sticker %s", attachment)
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
            data,
            {},
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
            attachment_data = asyncio.run(
                self._process_telegram_attachment(effective_attachment)
            )
            if attachment_data:
                attachments.append(attachment_data)
        if len(body) > 0 or attachments:
            author = self._get_author(chat.gateway_id, update)
            new_message = chat.message_post(
                body=body,
                author_id=author._name == "res.partner" and author.id,
                gateway_type="telegram",
                date=update.message.date.replace(tzinfo=None),
                # message_id=update.message.message_id,
                subtype_xmlid="mail.mt_comment",
                message_type="comment",
                attachments=attachments,
            )
            self._post_process_message(new_message, chat)
            related_message_id = (
                update.message.reply_to_message and update.message.reply_to_message.id
            )
            if related_message_id:
                related_message = (
                    self.env["mail.notification"]
                    .search(
                        [
                            ("gateway_channel_id", "=", chat.id),
                            ("gateway_message_id", "=", related_message_id),
                        ]
                    )
                    .mail_message_id
                )
                if related_message and related_message.gateway_message_id:
                    new_related_message = (
                        self.env[related_message.gateway_message_id.model]
                        .browse(related_message.gateway_message_id.res_id)
                        .message_post(
                            body=body,
                            author_id=author._name == "res.partner" and author.id,
                            gateway_type="telegram",
                            date=update.message.date.replace(tzinfo=None),
                            # message_id=update.message.message_id,
                            subtype_xmlid="mail.mt_comment",
                            message_type="comment",
                            attachments=attachments,
                        )
                    )
                    new_message.gateway_message_id = new_related_message
                    self._post_process_reply(related_message)
            return new_message

    async def _send_telegram(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        bot = self._get_telegram_bot(gateway.token)
        await bot.initialize()
        chat = await bot.get_chat(record.gateway_channel_id.gateway_channel_token)
        message = False
        body = self._get_message_body(record)
        if body:
            message = await chat.send_message(
                html2plaintext(body), parse_mode=parse_mode
            )
        for attachment in record.mail_message_id.attachment_ids:
            # Remember that files are limited to 50 Mb on Telegram
            # https://core.telegram.org/bots/faq#handling-media
            if attachment.mimetype.split("/")[0] == "image":
                new_message = await chat.send_photo(BytesIO(attachment.raw))
            else:
                new_message = await chat.send_document(
                    BytesIO(attachment.raw),
                    filename=attachment.name,
                )
            if not message:
                message = new_message
        return message

    def _send(
        self,
        gateway,
        record,
        auto_commit=False,
        raise_exception=False,
        parse_mode=False,
    ):
        message = False
        try:
            message = asyncio.run(
                self._send_telegram(
                    gateway,
                    record,
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    parse_mode=parse_mode,
                )
            )
        except Exception as exc:
            buff = StringIO()
            traceback.print_exc(file=buff)
            _logger.error(buff.getvalue())
            if raise_exception:
                raise MailDeliveryException(
                    _("Unable to send the telegram message"), exc
                ) from None
            else:
                _logger.warning(
                    "Issue sending message with id {}: {}".format(record.id, exc)
                )
                record.sudo().write(
                    {
                        "notification_status": "exception",
                        "failure_reason": exc,
                        "failure_type": "unknown",
                    }
                )
        if message:
            record.sudo().write(
                {
                    "notification_status": "sent",
                    "failure_reason": False,
                    "failure_type": False,
                    "gateway_message_id": message.id,
                }
            )
        self.env["bus.bus"]._sendone(
            record.gateway_channel_id,
            "mail.message/insert",
            {
                "id": record.mail_message_id.id,
                "gateway_type": record.mail_message_id.gateway_type,
            },
        )
        if auto_commit is True:
            # pylint: disable=invalid-commit
            self.env.cr.commit()

    def _get_author_vals(self, gateway, update):
        names = []
        for name in [
            update.message.from_user.first_name or False,
            update.message.from_user.last_name or False,
        ]:
            if name:
                names.append(name)
        return {
            "name": " ".join(names),
            "gateway_id": gateway.id,
            "gateway_token": str(update.message.from_user.id),
        }

    def _get_author(self, gateway, update):
        author_id = update.message.from_user.id
        if author_id:
            gateway_partner = self.env["res.partner.gateway.channel"].search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("gateway_token", "=", str(author_id)),
                ]
            )
            if gateway_partner:
                return gateway_partner.partner_id
            guest = self.env["mail.guest"].search(
                [
                    ("gateway_id", "=", gateway.id),
                    ("gateway_token", "=", str(author_id)),
                ]
            )
            if guest:
                return guest
            return self.env["mail.guest"].create(self._get_author_vals(gateway, update))

        return super()._get_author(gateway, update)

    async def _async_update_content_after_hook(self, channel, message):
        bot = self._get_telegram_bot(channel.gateway_id.token)
        await bot.initialize()
        await bot.edit_message_text(
            html2plaintext(message.body),
            chat_id=int(channel.gateway_channel_token),
            message_id=int(
                message.gateway_notification_ids.mapped("gateway_message_id")[0]
            ),
        )

    def _update_content_after_hook(self, channel, message):
        asyncio.run(self._async_update_content_after_hook(channel, message))
