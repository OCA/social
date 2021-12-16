# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging
import mimetypes
from io import BytesIO

from odoo import api, models
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

try:
    import telegram
    from lottie.exporters import exporters
    from lottie.importers import importers
except (ImportError, IOError) as err:
    _logger.debug(err)


class MailBrokerChannel(models.Model):

    _inherit = "mail.broker.channel"

    @api.returns("mail.message.broker", lambda value: value.id)
    def telegram_message_post_broker(self, body=False, **kwargs):
        return self.message_post_broker(body=body, broker_type="telegram", **kwargs)

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

    def telegram_update(self, update):
        self.ensure_one()
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
                    % (effective_attachment.latitude, effective_attachment.longitude,)
                )
            attachment_data = self._process_telegram_attachment(effective_attachment)
            if attachment_data:
                attachments.append(attachment_data)
        if len(body) > 0 or attachments:
            return self.message_post_broker(
                body=body,
                broker_type="telegram",
                date=update.message.date.replace(tzinfo=None),
                message_id=update.message.message_id,
                subtype="mt_comment",
                attachments=attachments,
            )
