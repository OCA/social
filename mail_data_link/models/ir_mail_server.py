# Copyright 2019 Therp BV <https://therp.nl>
# Copyright 2022 Opener B.V. <stefan@opener.amsterdam>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from lxml.html import fromstring, tostring

from odoo import models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

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
        """Override to replace internal (data-oe) links with absolute URIs"""
        email = super(IrMailServer, self).build_email(
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
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        for part in email.walk():
            if part.get_content_type() == "text/html":
                body = part.get_content()
                if not body or body == "\n":
                    continue
                root = fromstring(body)
                for link in root.xpath(".//a[@data-oe-model][@data-oe-id][@href='#']"):
                    model = link.attrib["data-oe-model"]
                    res_id = link.attrib["data-oe-id"]
                    link.set(
                        "href", f"{base_url}/mail/view?model={model}&res_id={res_id}"
                    )
                payload = tostring(root)
                part.set_content(payload, "text", "html")
        return email
