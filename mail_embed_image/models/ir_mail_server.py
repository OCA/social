import logging
import uuid
from base64 import b64encode
from email.mime.image import MIMEImage

import requests
from lxml.html import fromstring, tostring

from odoo import models

_logger = logging.getLogger(__name__)


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
        fileparts = None
        if subtype == "html":
            body, fileparts = self._build_email_replace_img_src(body)
        result = super(IrMailServer, self).build_email(
            email_from=email_from,
            email_to=email_to,
            subject=subject,
            body=body,
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
        if fileparts:
            for fpart in fileparts:
                result.attach(fpart)
        return result

    def _build_email_replace_img_src(self, html_body):
        """Replace img src with base64 encoded image."""
        if not html_body:
            return html_body

        root = fromstring(html_body)
        images = root.xpath("//img")
        fileparts = []
        for img in images:
            src = img.get("src")
            if src and not src.startswith("data:") and not src.startswith("base64:"):
                try:
                    response = requests.get(src, timeout=10)
                    _logger.debug("Fetching image from %s", src)
                    if response.status_code == 200:
                        cid = uuid.uuid4().hex
                        # convert cid to rfc2047 encoding
                        filename_encoded = "=?utf-8?b?%s?=" % b64encode(
                            cid.encode("utf-8")
                        ).decode("utf-8")
                        image_content = response.content
                        filepart = MIMEImage(image_content)
                        filepart.add_header("Content-ID", f"<{cid}>")
                        filepart.add_header(
                            "Content-Disposition",
                            "inline",
                            filename=filename_encoded,
                        )
                        img.set("src", f"cid:{cid}")
                        fileparts.append(filepart)
                except Exception as e:
                    _logger.warning("Could not get %s: %s", img.get("src"), str(e))
        return tostring(root, encoding="unicode"), fileparts
