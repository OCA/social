# Copyright 2025 Lambdao
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_deduplicate_attachments(self, attachments):
        if attachments:  # this is an enumerable of _Attachment named tuples
            domain = [("res_id", "in", self.ids), ("res_model", "=", self._name)]
            Attachments = self.env["ir.attachment"]
            checksums = [
                r["checksum"]
                for r in Attachments.search_read(domain, fields=["checksum"])
            ]
            checksum = Attachments._compute_checksum
            # we use a[1] instead of a.content because some modules might use
            # simple tuples instead of named tuples...
            attachments = [a for a in attachments if checksum(a[1]) not in checksums]
        return attachments  # if it's None there's nothing to do

    def _message_deduplicate_attachment_ids(self, attachment_ids):
        # we let the mail_attachment_upload function create a dup with a res_id 0
        # for the pending message. Here we simply reuse an existing attachment,
        # so the dup will be GCed like any attachment for an unsent message
        res = []
        if attachment_ids:
            domain = [("res_id", "in", self.ids), ("res_model", "=", self._name)]
            Attachments = self.env["ir.attachment"]
            id_checksum_list = Attachments.search_read(domain, fields=["checksum"])
            id_by_checksum = {r["checksum"]: r["id"] for r in id_checksum_list}
            for attachment_id in attachment_ids:
                checksum = Attachments.browse(attachment_id).checksum
                if checksum in id_by_checksum:
                    res.append(id_by_checksum[checksum])
                else:
                    res.append(attachment_id)
        return res

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
        **kwargs
    ):
        attachments = self._message_deduplicate_attachments(attachments)
        attachment_ids = self._message_deduplicate_attachment_ids(attachment_ids)
        return super().message_post(
            body=body,
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
            **kwargs
        )
