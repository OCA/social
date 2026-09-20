# Copyright (C) 2024 - KMEE
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import logging
import re

import lxml.html
from lxml import etree

from odoo import models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _collect_inline_references(self, body):
        """Collect CIDs and filenames referenced in body.

        Returns a tuple (inline_cids, inline_names) with sets of referenced
        CIDs and filenames.
        """
        inline_cids = set()
        inline_names = set()
        if not body:
            return inline_cids, inline_names

        try:
            root = lxml.html.fromstring(ustr(body))
        except (etree.ParserError, etree.XMLSyntaxError, ValueError) as error:
            _logger.warning("Could not parse body for inline references: %s", error)
            return inline_cids, inline_names

        for node in root.iter("img"):
            src = node.get("src", "")
            if src.startswith("cid:"):
                inline_cids.add(src[len("cid:") :])
            filename = node.get("data-filename")
            if filename:
                inline_names.add(filename)

        return inline_cids, inline_names

    def _collect_inline_attachment_names(self, attachments, inline_cids, inline_names):
        """Return the names of ``attachments`` tuples that are inline.

        An attachment is inline when its CID is referenced in the body
        (``cid:...``) or its filename matches a ``data-filename`` reference.
        Matching by name instead of list position keeps detection correct
        even when existing ``attachment_ids`` are linked alongside.
        """
        inline_attachment_names = set()
        if not attachments or not (inline_cids or inline_names):
            return inline_attachment_names

        for attachment in attachments:
            if len(attachment) < 2:
                continue
            name = attachment[0]
            info = attachment[2] if len(attachment) >= 3 else None
            cid = info.get("cid") if isinstance(info, dict) else None
            if (cid and cid in inline_cids) or name in inline_names:
                inline_attachment_names.add(name)

        return inline_attachment_names

    def _find_inline_attachments_from_body(self, processed_body, body, new_attachments):
        """Return new attachments referenced via /web/image/{id} in the body."""
        inline_attachments = self.env["ir.attachment"].sudo()
        body_to_check = processed_body or body
        if not body_to_check or "/web/image/" not in body_to_check:
            return inline_attachments

        try:
            root = lxml.html.fromstring(ustr(body_to_check))
        except (etree.ParserError, etree.XMLSyntaxError, ValueError) as error:
            _logger.warning(
                "Could not parse processed body for inline images: %s", error
            )
            return inline_attachments

        attachments_by_id = {att.id: att for att in new_attachments}
        for node in root.iter("img"):
            src = node.get("src", "")
            for attachment_id in re.findall(r"/web/image/(\d+)", src):
                attachment = attachments_by_id.get(int(attachment_id))
                if attachment:
                    inline_attachments |= attachment

        return inline_attachments

    def _unlink_inline_attachments(self, inline_attachments, model, res_id):
        """Detach inline attachments from the record, keeping them on the message."""
        if not inline_attachments:
            return

        _logger.info(
            "Detaching %d inline attachment(s) from record [%s] %s: %s",
            len(inline_attachments),
            model,
            res_id,
            sorted(inline_attachments.ids),
        )
        inline_attachments.write({"res_model": False, "res_id": False})

    def _message_post_process_attachments(
        self, attachments, attachment_ids, message_values
    ):
        """Keep inline attachments out of the record attachment list.

        Inline attachments (referenced by CID/filename or via
        ``/web/image/<id>`` in the body) are detached from the record while
        staying linked to the message for rendering. Only newly created
        attachments are considered, so previously linked attachments passed
        through ``attachment_ids`` are never touched.
        """
        body = message_values.get("body")
        model = message_values.get("model")
        res_id = message_values.get("res_id")

        inline_cids, inline_names = self._collect_inline_references(body)
        inline_attachment_names = self._collect_inline_attachment_names(
            attachments, inline_cids, inline_names
        )

        return_values = super()._message_post_process_attachments(
            attachments, attachment_ids, message_values
        )

        if not model or not res_id:
            return return_values

        linked_ids = [
            command[1]
            for command in return_values.get("attachment_ids", [])
            if isinstance(command, (list, tuple)) and command[0] == 4
        ]
        existing_ids = set(attachment_ids or [])
        new_attachment_ids = [aid for aid in linked_ids if aid not in existing_ids]
        if not new_attachment_ids:
            return return_values

        new_attachments = self.env["ir.attachment"].sudo().browse(new_attachment_ids)

        inline_attachments = self.env["ir.attachment"].sudo()
        if inline_attachment_names:
            inline_attachments |= new_attachments.filtered(
                lambda att: att.name in inline_attachment_names
            )
        inline_attachments |= self._find_inline_attachments_from_body(
            return_values.get("body"), body, new_attachments
        )

        self._unlink_inline_attachments(inline_attachments, model, res_id)

        return return_values
