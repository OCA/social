# Copyright (C) 2024 - KMEE
# License LGPL-3 - See http://www.gnu.org/licenses/lgpl-3.0.html

import logging
import re

import lxml.html

from odoo import models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _collect_inline_references(self, body):
        """Collect CIDs and filenames referenced in body.

        Returns a tuple (inline_cids, inline_names) with sets of
        referenced CIDs and filenames.
        """
        inline_cids = set()
        inline_names = set()
        if not body:
            return inline_cids, inline_names

        try:
            root = lxml.html.fromstring(ustr(body))
            for node in root.iter("img"):
                src = node.get("src", "")
                # Check for CID references (cid:xxx)
                if src.startswith("cid:"):
                    cid = src.split("cid:")[1]
                    inline_cids.add(cid)
                # Check for data-filename attribute
                filename = node.get("data-filename")
                if filename:
                    inline_names.add(filename)
        except Exception as e:
            _logger.warning("Erro ao processar body para detectar anexos inline: %s", e)

        return inline_cids, inline_names

    def _identify_inline_attachments(
        self, attachments, inline_cids, inline_names, model, res_id
    ):
        """Identify which attachments are inline based on CID or filename.

        Returns a set of indices of inline attachments.
        """
        inline_indices = set()
        if not (inline_cids or inline_names):
            return inline_indices

        for idx, attachment in enumerate(attachments):
            if len(attachment) < 2:
                continue
            name = attachment[0]
            info = attachment[2] if len(attachment) >= 3 else None
            cid = info and info.get("cid")
            if cid and cid in inline_cids:
                inline_indices.add(idx)
                _logger.info(
                    "Anexo inline detectado por CID [%s] ID %s: %s (CID: %s)",
                    model,
                    res_id,
                    name,
                    cid,
                )
            elif name in inline_names:
                inline_indices.add(idx)
                _logger.info(
                    "Anexo inline detectado por filename [%s] ID %s: %s",
                    model,
                    res_id,
                    name,
                )

        return inline_indices

    def _find_inline_attachments_from_body(self, processed_body, body, new_attachments):
        """Find inline attachments from /web/image/{id} references in body.

        Returns a recordset of inline attachments found in the body.
        """
        inline_attachments = self.env["ir.attachment"].sudo()
        body_to_check = processed_body or body
        if not body_to_check:
            return inline_attachments

        try:
            root = lxml.html.fromstring(ustr(body_to_check))
            for node in root.iter("img"):
                src = node.get("src", "")
                matches = re.findall(r"/web/image/(\d+)", src)
                for mid in matches:
                    attachment_id = int(mid)
                    matching_att = new_attachments.filtered(
                        lambda a, aid=attachment_id: a.id == aid
                    )
                    if matching_att:
                        inline_attachments |= matching_att
        except Exception as e:
            _logger.warning("Erro ao processar body processado: %s", e)

        return inline_attachments

    def _unlink_inline_attachments(self, inline_attachments, model, res_id):
        """Unlink inline attachments from the record."""
        if not inline_attachments:
            return

        _logger.info(
            "Desvinculando %d anexos inline do registro [%s] ID %s: %s",
            len(inline_attachments),
            model,
            res_id,
            sorted(inline_attachments.mapped("id")),
        )
        # Unlink inline attachments from the record
        # They will remain linked only to the message
        inline_attachments.write(
            {
                "res_model": False,
                "res_id": False,
            }
        )

    def _message_post_process_attachments(
        self, attachments, attachment_ids, message_values
    ):
        """Override to prevent inline attachments from being linked to the record.

        Inline attachments (with CID or referenced in body) will be created
        without res_model and res_id, so they won't appear in the attachment
        list of the record. They will still be accessible via the message body.
        """
        body = message_values.get("body")
        model = message_values.get("model")
        res_id = message_values.get("res_id")

        # Collect CIDs and filenames referenced in body BEFORE processing
        inline_cids, inline_names = self._collect_inline_references(body)

        # Identify which attachments are inline based on CID or filename
        inline_indices = self._identify_inline_attachments(
            attachments, inline_cids, inline_names, model, res_id
        )

        # Process attachments normally first
        return_values = super()._message_post_process_attachments(
            attachments, attachment_ids, message_values
        )

        if not inline_indices or not model or not res_id:
            return return_values

        # Get newly created attachments from return values
        m2m_attachment_ids = return_values.get("attachment_ids", [])
        new_attachment_ids = [
            cmd[1]
            for cmd in m2m_attachment_ids
            if isinstance(cmd, tuple) and cmd[0] == 4
        ]

        if not new_attachment_ids:
            return return_values

        # Map inline indices to attachment IDs
        # Note: attachments list order should match new_attachments order
        new_attachments = self.env["ir.attachment"].sudo().browse(new_attachment_ids)

        # Find which of the new attachments correspond to inline ones
        # We need to match by position in the list
        inline_attachments = self.env["ir.attachment"].sudo()
        for idx in inline_indices:
            if idx < len(new_attachments):
                inline_attachments |= new_attachments[idx]

        # Also check body after processing for /web/image/{id} references
        processed_body = return_values.get("body")
        inline_from_body = self._find_inline_attachments_from_body(
            processed_body, body, new_attachments
        )
        inline_attachments |= inline_from_body

        # Unlink inline attachments from the record
        self._unlink_inline_attachments(inline_attachments, model, res_id)

        return return_values
