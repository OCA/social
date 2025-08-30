# Copyright 2025 Lambdao
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

import lxml.html
from markupsafe import Markup

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_deduplicate_attachments(self, attachments, body=None):
        """
        Deduplicate attachments and update body CID references.

        Instead of dropping duplicate attachments, this method:
        1. Identifies duplicate attachments by checksum
        2. For duplicates, finds the existing attachment
        3. Updates CID references in the body to point to existing attachments
        4. Returns deduplicated attachment list and updated body
        """
        if not attachments:
            return attachments, body

        domain = [("res_id", "in", self.ids), ("res_model", "=", self._name)]
        Attachments = self.env["ir.attachment"]
        existing_attachments = Attachments.search_read(
            domain, fields=["checksum", "id", "access_token"]
        )
        checksum_to_attachment = {att["checksum"]: att for att in existing_attachments}

        checksum = Attachments._compute_checksum
        filtered_attachments = []
        cid_mapping = {}

        for attachment in attachments:
            if len(attachment) >= 3:
                _name, content, info = attachment[0], attachment[1], attachment[2] or {}
            elif len(attachment) == 2:
                _name, content, info = attachment[0], attachment[1], {}
            else:
                continue

            attachment_checksum = checksum(content)

            if attachment_checksum in checksum_to_attachment:
                existing_att = checksum_to_attachment[attachment_checksum]
                cid = info.get("cid")
                if cid:
                    access_token = existing_att.get("access_token")
                    if not access_token:
                        existing_record = Attachments.browse(existing_att["id"])
                        access_token = existing_record._generate_access_token()
                        existing_record.write({"access_token": access_token})

                    cid_mapping[cid] = {"id": existing_att["id"], "token": access_token}
            else:
                filtered_attachments.append(attachment)

        if cid_mapping and body:
            body = self._update_body_cid_references(body, cid_mapping)
        return filtered_attachments, body

    def _update_body_cid_references(self, body, cid_mapping):
        """Update CID references in body to point to existing attachments."""
        if not body or not cid_mapping:
            return body
        try:
            root = lxml.html.fromstring(body)
            postprocessed = False
            for node in root.iter("img"):
                if node.get("src", "").startswith("cid:"):
                    cid = node.get("src").split("cid:")[1]
                    if cid in cid_mapping:
                        att_info = cid_mapping[cid]
                        node.set(
                            "src",
                            f"/web/image/{att_info['id']}?access_token={att_info['token']}",
                        )
                        postprocessed = True
            if postprocessed:
                return Markup(  # noqa: S704
                    lxml.html.tostring(root, pretty_print=False, encoding="unicode")
                )
        except (ValueError, lxml.etree.XMLSyntaxError):  # pylint: disable=except-pass
            pass  # If parsing fails, return original body
        return body

    def _message_deduplicate_attachment_ids(self, attachment_ids, body=None):
        """
        Deduplicate attachment IDs by replacing duplicates with existing ones.
        Also updates body references to point to existing attachments.
        """
        if not attachment_ids:
            return attachment_ids, body

        domain = [("res_id", "in", self.ids), ("res_model", "=", self._name)]
        Attachments = self.env["ir.attachment"]
        existing_attachments = Attachments.search_read(
            domain, fields=["checksum", "id", "access_token"]
        )
        id_by_checksum = {r["checksum"]: r["id"] for r in existing_attachments}
        checksum_to_attachment = {att["checksum"]: att for att in existing_attachments}

        res = []
        attachment_id_mapping = {}  # Maps old attachment ID to new attachment info

        for attachment_id in attachment_ids:
            attachment = Attachments.browse(attachment_id)
            checksum = attachment.checksum
            if checksum in id_by_checksum:
                # Use existing attachment instead of duplicate
                existing_att_id = id_by_checksum[checksum]
                res.append(existing_att_id)

                # Store mapping for body update
                existing_att = checksum_to_attachment[checksum]
                access_token = existing_att.get("access_token")
                if not access_token:
                    existing_record = Attachments.browse(existing_att_id)
                    access_token = existing_record._generate_access_token()
                    existing_record.write({"access_token": access_token})

                attachment_id_mapping[attachment_id] = {
                    "id": existing_att_id,
                    "token": access_token,
                }
            else:
                res.append(attachment_id)

        # Update body to replace attachment references if any mappings exist
        updated_body = body
        if attachment_id_mapping and body:
            updated_body = self._update_body_attachment_references(
                body, attachment_id_mapping
            )

        return res, updated_body

    def _update_body_attachment_references(self, body, attachment_id_mapping):  # noqa: C901
        """Update attachment references in body to point to existing attachments."""
        if not body or not attachment_id_mapping:
            return body
        try:
            root = lxml.html.fromstring(body)
            postprocessed = False

            for node in root.iter("img"):
                data_attachment_id = node.get("data-attachment-id")
                if data_attachment_id:
                    try:
                        old_attachment_id = int(data_attachment_id)
                        if old_attachment_id in attachment_id_mapping:
                            att_info = attachment_id_mapping[old_attachment_id]
                            node.set("data-attachment-id", str(att_info["id"]))
                            postprocessed = True
                    except (ValueError, TypeError):  # pylint: disable=except-pass
                        pass

                # Check for /web/image/ URLs in src attribute
                src = node.get("src", "")
                if "/web/image/" in src:
                    for old_id, att_info in attachment_id_mapping.items():
                        # Match patterns like
                        # /web/image/1066-eb8c51b1/filename.jpg?access_token=...
                        # or /web/image/1066?access_token=...
                        if f"/web/image/{old_id}" in src:
                            new_src = src.replace(
                                f"/web/image/{old_id}", f"/web/image/{att_info['id']}"
                            )
                            if "access_token=" in new_src:
                                new_src = re.sub(
                                    r"access_token=[^&]*",
                                    f"access_token={att_info['token']}",
                                    new_src,
                                )
                            node.set("src", new_src)
                            postprocessed = True
                            break

            if postprocessed:
                return Markup(  # noqa: S704
                    lxml.html.tostring(root, pretty_print=False, encoding="unicode")
                )
        except (ValueError, lxml.etree.XMLSyntaxError):  # pylint: disable=except-pass
            pass  # If parsing fails, return original body
        return body

    @api.returns("mail.message", lambda value: value.id)
    def message_post(
        self,
        *,
        body="",
        subject=None,
        message_type="notification",
        email_from=None,
        author_id=None,
        parent_id=False,
        subtype_xmlid=None,
        subtype_id=False,
        partner_ids=None,
        attachments=None,
        attachment_ids=None,
        **kwargs,
    ):
        attachments, updated_body = self._message_deduplicate_attachments(
            attachments, body
        )
        attachment_ids, updated_body = self._message_deduplicate_attachment_ids(
            attachment_ids, updated_body
        )

        return super().message_post(
            body=updated_body,
            subject=subject,
            message_type=message_type,
            email_from=email_from,
            author_id=author_id,
            parent_id=parent_id,
            subtype_xmlid=subtype_xmlid,
            subtype_id=subtype_id,
            partner_ids=partner_ids,
            attachments=attachments,
            attachment_ids=attachment_ids,
            **kwargs,
        )
