# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import threading

from odoo import api, models, tools


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def _tracking_headers_add(self, tracking_email_id, headers):
        """Allow other addons to add its own tracking SMTP headers"""
        headers = headers or {}
        headers["X-Odoo-Database"] = getattr(threading.currentThread(), "dbname", None)
        headers["X-Odoo-MailTracking-ID"] = tracking_email_id
        return headers

    def _tracking_email_id_body_get(self, body):
        body = body or ""
        # https://regex101.com/r/lW4cB1/2
        match = re.search(r'<img[^>]*data-odoo-tracking-email=["\']([0-9]*)["\']', body)
        return int(match.group(1)) if match and match.group(1) else False

    def build_email(
        self,
        email_from,
        email_to,
        subject,
        body,
        email_cc=None,
        email_bcc=None,
        reply_to=False,
        attachments=None,
        message_id=None,
        references=None,
        object_id=False,
        subtype="plain",
        headers=None,
        body_alternative=None,
        subtype_alternative="plain",
    ):
        tracking_email_id = self._tracking_email_id_body_get(body)
        if tracking_email_id:
            headers = self._tracking_headers_add(tracking_email_id, headers)
        msg = super(IrMailServer, self).build_email(
            email_from,
            email_to,
            subject,
            body,
            email_cc=email_cc,
            email_bcc=email_bcc,
            reply_to=reply_to,
            attachments=attachments,
            message_id=message_id,
            references=references,
            object_id=object_id,
            subtype=subtype,
            headers=headers,
            body_alternative=body_alternative,
            subtype_alternative=subtype_alternative,
        )
        return msg

    def _tracking_email_get(self, message):
        try:
            tracking_email_id = int(
                message.get(
                    "X-Odoo-MailTracking-ID",
                    # Deprecated tracking header, kept as fallback
                    message["X-Odoo-Tracking-ID"],
                )
            )
        except (TypeError, ValueError, KeyError):
            tracking_email_id = False
        return self.env["mail.tracking.email"].browse(tracking_email_id)

    def _smtp_server_get(self, mail_server_id, smtp_server):
        smtp_server_used = False
        mail_server = None
        if mail_server_id:
            mail_server = self.browse(mail_server_id)
        elif not smtp_server:
            mail_server_ids = self.search([], order="sequence", limit=1)
            mail_server = mail_server_ids[0] if mail_server_ids else None
        if mail_server:
            smtp_server_used = mail_server.smtp_host
        else:
            smtp_server_used = smtp_server or tools.config.get("smtp_server")
        return smtp_server_used

    @api.model
    def send_email(
        self,
        message,
        mail_server_id=None,
        smtp_server=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_encryption=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        message_id = False
        tracking_email = self._tracking_email_get(message)
        smtp_server_used = self.sudo()._smtp_server_get(mail_server_id, smtp_server)
        try:
            message_id = super(IrMailServer, self).send_email(
                message,
                mail_server_id=mail_server_id,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_encryption=smtp_encryption,
                smtp_debug=smtp_debug,
                smtp_session=smtp_session,
            )
        except Exception as e:
            if tracking_email:
                tracking_email.smtp_error(self, smtp_server_used, e)
        if message_id and tracking_email:
            vals = tracking_email._tracking_sent_prepare(
                self, smtp_server_used, message, message_id
            )
            if vals:
                self.env["mail.tracking.event"].sudo().create(vals)
        return message_id
