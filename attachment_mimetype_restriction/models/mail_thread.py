# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging

from markupsafe import escape

from odoo import _, models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _evaluate_attachment_against_allowlist(
        self, name, content, info, allowed_mimetypes
    ):
        try:
            if isinstance(content, str):
                encoding = info and info.get("encoding")
                try:
                    content_bytes = content.encode(encoding or "utf-8")
                except UnicodeEncodeError:
                    _logger.debug(
                        "Encoding '%s' failed for attachment '%s'; "
                        "retrying as utf-8",
                        encoding,
                        name,
                    )
                    content_bytes = content.encode("utf-8")
            else:
                content_bytes = content
            temp_vals = {
                "name": name,
                "datas": base64.b64encode(content_bytes),
            }
            mimetype = self.env["ir.attachment"]._compute_mimetype(temp_vals)
        except Exception as e:
            _logger.warning(
                "Pre-validation failed for attachment '%s' (%s); blocking by default",
                name,
                e,
            )
            return {"name": name, "mimetype": _("could not be analyzed")}
        if mimetype not in allowed_mimetypes:
            return {"name": name, "mimetype": mimetype}
        return None

    def _message_post_process_attachments(
        self, attachments, attachment_ids, message_values
    ):
        model = message_values.get("model")
        res_id = message_values.get("res_id")
        target_record = None
        if model and res_id and model in self.env:
            target_record = self.env[model].browse(res_id).exists() or None
        if (
            target_record
            and "company_id" in target_record._fields
            and target_record.company_id
        ):
            company_id = target_record.company_id.id
        else:
            company_id = self.env.company.id
        allowed_mimetypes = self.env["ir.attachment"]._get_allowed_mimetypes(
            company_id, model
        )
        blocked_attachments_info = []
        if attachments and allowed_mimetypes:
            filtered_attachments = []
            for attachment in attachments:
                if len(attachment) == 2:
                    name, content = attachment
                    info = {}
                elif len(attachment) == 3:
                    name, content, info = attachment
                else:
                    filtered_attachments.append(attachment)
                    continue
                blocked_info = self._evaluate_attachment_against_allowlist(
                    name, content, info, allowed_mimetypes
                )
                if blocked_info:
                    blocked_attachments_info.append(blocked_info)
                    continue
                filtered_attachments.append(attachment)
            attachments = filtered_attachments
        if attachment_ids and allowed_mimetypes:
            existing = self.env["ir.attachment"].sudo().browse(attachment_ids).exists()
            blocked_existing = existing.filtered(
                lambda a: a.mimetype and a.mimetype not in allowed_mimetypes
            )
            if blocked_existing:
                for att in blocked_existing:
                    blocked_attachments_info.append(
                        {"name": att.name, "mimetype": att.mimetype}
                    )
                attachment_ids = (existing - blocked_existing).ids
        result = super()._message_post_process_attachments(
            attachments, attachment_ids, message_values
        )
        if blocked_attachments_info and not target_record:
            _logger.warning(
                "Blocked %d attachment(s) but no target record to notify on "
                "(model=%s, res_id=%s)",
                len(blocked_attachments_info),
                model,
                res_id,
            )
        if blocked_attachments_info and target_record:
            blocked_list = []
            for blocked in blocked_attachments_info:
                blocked_list.append(
                    "<li><strong>%s</strong> (%s)</li>"
                    % (escape(blocked["name"]), escape(blocked["mimetype"]))
                )
            notification_body = _(
                '<div class="o_mail_notification">'
                "<p><strong>Security Notice: Blocked Attachments</strong></p>"
                "<p>The following attachment(s) were blocked:</p>"
                "<ul>%s</ul>"
                "<p><em>These file types are not allowed by your organization's "
                "security policy.</em></p>"
                "</div>"
            ) % "".join(blocked_list)
            try:
                target_record.sudo().message_post(
                    body=notification_body,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
            except Exception as e:
                _logger.warning("Could not post blocked attachment notification: %s", e)
        return result
