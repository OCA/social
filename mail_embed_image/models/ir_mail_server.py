# Copyright 2019 Therp BV <https://therp.nl>
# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import uuid
from base64 import b64encode
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

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
        image_embedding_method = self.env.company.image_embedding_method
        fileparts = None
        if subtype == "html" and image_embedding_method != "none":
            body, fileparts = self._build_email_replace_img_src(body)

        # TODO check if we can add attachments here.
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
            # Multipart method MUST be multipart/related for CIDs embedding
            # Gmail and Office won't process the images otherwise
            if image_embedding_method == "cid":
                result.set_type("multipart/related")
            for fpart in fileparts:
                result.attach(fpart)
            # after all part where added, we need to reorganize the parts
            #
            # Before:
            # - boundary 1
            #   - text/plain
            #   - text/html
            #   - image/png
            # After:
            # - boundary 1
            #   - multipart/alternative
            #     - boundary 2
            #       - text/plain
            #       - text/html
            #   - image/png
            # If an attachment is present, the parts are already in the right
            # order in this case, we don't need to reorganize the parts
            # but if we find later text/plain or text/html parts, we will need
            # to append them to the first multipart/alternative.
            #
            # It possible to have multiple parts of type multipart/alternative,
            # but it's not a common case.
            all_parts = []
            for part in result.iter_parts():
                if part.get_content_type() == "multipart/alternative":
                    all_parts.append(part)

            if not all_parts:
                all_parts = [MIMEMultipart("alternative")]

            for part in result.iter_parts():
                if part.get_content_type() in ["text/html", "text/plain"]:
                    all_parts[0].attach(part)
                elif part.get_content_type() == "multipart/alternative":
                    pass
                else:
                    all_parts.append(part)
            result.set_payload(all_parts)
        return result

    def _build_email_replace_img_src(self, html_body):
        """Replace img src with base64 encoded image."""
        if not html_body:
            return html_body

        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        image_embedding_method = self.env.company.image_embedding_method
        root = fromstring(html_body)
        fileparts = []
        # Limit results to only internal resources to avoid malicious external
        # image injections
        for img in root.xpath(
            ".//img[starts-with(@src, '%s')]"
            "| .//img[starts-with(@src, '/web/image')]" % (base_url)
        ):
            image_path = img.get("src")
            try:
                response = requests.get(image_path, timeout=10)
                _logger.debug("Fetching image from %s", image_path)
                if response.status_code == 200:
                    image_content = response.content
                    filepart = MIMEImage(image_content)
                    if image_embedding_method == "data":
                        raw_content = filepart.get_payload(decode=True)
                        base_64_content = b64encode(raw_content).decode("utf-8")
                        mimetype = filepart.get_content_type()
                        img.set("src", f"data:{mimetype};base64,{base_64_content}")
                    elif image_embedding_method == "cid":
                        cid = uuid.uuid4().hex
                        # convert cid to rfc2047 encoding
                        filename_encoded = "=?utf-8?b?%s?=" % b64encode(
                            cid.encode("utf-8")
                        ).decode("utf-8")
                        filepart.add_header("Content-ID", f"<{cid}>")
                        filepart.add_header(
                            "Content-Disposition",
                            "inline",
                            filename=filename_encoded,
                        )
                        img.set("src", f"cid:{cid}")
                        fileparts.append(filepart)
                else:
                    _logger.warning(
                        "Could not get %s: HTTP status code %s",
                        img.get("src"),
                        response.status_code,
                    )
            except Exception as e:
                _logger.warning("Could not get %s: %s", img.get("src"), str(e))
        return tostring(root, encoding="unicode"), fileparts
