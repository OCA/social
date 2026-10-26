# Copyright (C) 2024 - KMEE
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import logging
import re

import lxml.html
from lxml import etree

from odoo import models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _get_inline_attachment_ids(self):
        """Return the ids of attachments rendered inline in the body.

        Inline images are rendered through ``/web/image/<id>`` URLs, so the
        attachments behind those URLs are considered inline. The substring
        guard avoids parsing the body when no inline image can be present.
        """
        self.ensure_one()
        inline_attachment_ids = set()

        if not self.body or "/web/image/" not in self.body:
            return inline_attachment_ids

        try:
            root = lxml.html.fromstring(ustr(self.body))
        except (etree.ParserError, etree.XMLSyntaxError, ValueError) as error:
            _logger.warning(
                "Could not parse body of message %s for inline images: %s",
                self.id,
                error,
            )
            return inline_attachment_ids

        for node in root.iter("img"):
            src = node.get("src", "")
            for attachment_id in re.findall(r"/web/image/(\d+)", src):
                inline_attachment_ids.add(int(attachment_id))

        return inline_attachment_ids

    def _message_format(self, fnames, format_reply=True):
        """Drop inline attachments from the formatted attachment list.

        Attachments referenced inline in the body are already rendered in the
        body and must not show up as attachment chips. Messages without
        attachment chips are skipped to avoid needless body parsing.
        """
        vals_list = super()._message_format(fnames, format_reply=format_reply)

        for vals in vals_list:
            formatted_attachments = vals.get("attachment_ids")
            if not formatted_attachments:
                continue

            inline_attachment_ids = self.browse(vals["id"])._get_inline_attachment_ids()
            if not inline_attachment_ids:
                continue

            vals["attachment_ids"] = [
                attachment
                for attachment in formatted_attachments
                if attachment.get("id") not in inline_attachment_ids
            ]

        return vals_list
