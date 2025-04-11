# Copyright 2025 ForgeFlow
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

import requests

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    smtp_authentication = fields.Selection(
        selection_add=[("mailgun", "Mailgun API")], ondelete={"mailgun": "set default"}
    )

    mail_mailgun_api_key = fields.Char(
        string="Mailgun API Key",
        help="API key for Mailgun.",
    )
    mail_mailgun_domain = fields.Char(
        string="Mailgun Domain",
        help="Domain for Mailgun.",
    )
    mail_mailgun_api_endpoint = fields.Char(
        string="Mailgun API Endpoint",
        help="API endpoint for Mailgun.",
    )

    def _compute_smtp_authentication_info(self):
        mailgun_servers = self.filtered(
            lambda server: server.smtp_authentication == "mailgun"
        )
        mailgun_servers.smtp_authentication_info = _(
            "Connect to the Mailgun API using the API key, domain, and endpoint."
        )
        mailgun_servers.smtp_host = 0
        mailgun_servers.smtp_port = 0

        return super(
            IrMailServer, self - mailgun_servers
        )._compute_smtp_authentication_info()

    def test_mailgun_api_connection(self):
        for server in self:
            try:
                api_key = server.mail_mailgun_api_key
                domain = server.mail_mailgun_domain
                api_endpoint = server.mail_mailgun_api_endpoint

                if not server.mail_mailgun_api_key or not server.mail_mailgun_domain:
                    raise ValueError(_("Mailgun API key and domain are required."))

                url = f"{api_endpoint}/domains/{domain}/connection"

                response = requests.get(url, auth=("api", api_key), timeout=60)
                response.raise_for_status()

            except Exception as e:
                raise UserError(
                    _(
                        "Connection Test Failed! Here is what we got instead:\n %s",
                        tools.ustr(e),
                    )
                ) from e

        message = _("Mailgun Api Connection Test Successful!")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

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
        smtp_ssl_certificate=None,
        smtp_ssl_private_key=None,
        smtp_debug=False,
        smtp_session=None,
    ):
        mail_server = self.browse(mail_server_id)
        if mail_server.smtp_authentication == "mailgun":
            return self._send_mailgun_email(message, mail_server)
        else:
            return super().send_email(
                message=message,
                mail_server_id=mail_server_id,
                smtp_server=smtp_server,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                smtp_encryption=smtp_encryption,
                smtp_ssl_certificate=smtp_ssl_certificate,
                smtp_ssl_private_key=smtp_ssl_private_key,
                smtp_debug=smtp_debug,
                smtp_session=smtp_session,
            )

    def _send_mailgun_email(self, message, mail_server):
        try:
            if (
                not mail_server.mail_mailgun_api_key
                or not mail_server.mail_mailgun_domain
            ):
                raise UserError(_("Mailgun API key and domain are required."))
            message_id = message.get("Message-ID")

            api_endpoint = mail_server.mail_mailgun_api_endpoint
            api_key = mail_server.mail_mailgun_api_key
            domain = mail_server.mail_mailgun_domain
            url = f"{api_endpoint}/{domain}/messages"

            email_from = tools.encapsulate_email(
                message.get("From"),
                self.env["ir.mail_server"]._get_default_from_address(),
            )
            body_plain, body_html, attachments = self._extract_email_data(message)
            files = self._convert_attachments_for_mailgun(attachments)
            payload = {
                "from": email_from,
                "to": message.get("To"),
                "subject": message.get("Subject"),
                "text": body_plain,
                "html": body_html,
                "h:X-Odoo-Message-Id": message_id,
            }

            response = requests.post(
                url, auth=("api", api_key), data=payload, files=files, timeout=60
            )
            response.raise_for_status()

        except Exception as e:
            msg = _("Mail delivery failed via Mailgun API with error: %s") % tools.ustr(
                e
            )
            _logger.error(msg)
        return message_id

    def _extract_email_data(self, message):
        body_plain = None
        body_html = None
        attachments = []

        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()

                if disposition == "attachment":
                    attachments.append(
                        (
                            part.get_filename(),
                            part.get_payload(decode=True),
                            content_type,
                        )
                    )
                elif content_type == "text/plain" and body_plain is None:
                    body_plain = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8"
                    )
                elif content_type == "text/html" and body_html is None:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8"
                    )
        else:
            content_type = message.get_content_type()
            payload = message.get_payload(decode=True)
            if content_type == "text/plain":
                body_plain = payload.decode(message.get_content_charset() or "utf-8")
            elif content_type == "text/html":
                body_html = payload.decode(message.get_content_charset() or "utf-8")

        return body_plain, body_html, attachments

    def _convert_attachments_for_mailgun(self, attachments):
        return [
            ("attachment", (filename, content, content_type))
            for filename, content, content_type in attachments
        ]
