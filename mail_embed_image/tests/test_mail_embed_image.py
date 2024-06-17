# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from base64 import b64encode

from lxml import html
from requests import get

from odoo.tests import common


class TestMailEmbedImage(common.TransactionCase):
    def test_mail_embed_image(self):
        """We pass a mail with <img src="..." /> tags to build_email,
        and then look into the result, check there were attachments
        created and you find xpaths like //img[src] have a cid"""
        # DATA
        base_url = self.env["ir.config_parameter"].get_param("web.base.url")
        image_url = base_url + "/mail_embed_image/static/description/icon.png"
        image = get(image_url, timeout=10).content
        body = html.tostring(
            html.fromstring(
                """
            <div>
            this is an email
            <img src="base64: %s"></img>
            <img src="%s"></img>
            </div>"""
                % (
                    # won't be hit because we ignore embedded images
                    b64encode(image),
                    # dito, not uploaded content
                    image_url,
                )
            )
        )
        email_from = "test@example.com"
        email_to = "test@example.com"
        subject = "test mail"
        # END DATA
        res = self.env["ir.mail_server"].build_email(
            email_from,
            [email_to],
            subject,
            body,
            subtype="html",
            subtype_alternative="plain",
        )
        images_in_mail = 0
        for part in res.walk():
            if part.get_content_type() == "text/html":
                # we do not search in text, just in case that texts exists in
                # the text elsewhere (not probable, but this is better)
                images_in_mail += len(
                    html.fromstring(part.get_payload(decode=True)).xpath(
                        "//img[starts-with(@src, 'cid:')]"
                    )
                )
        # verify 1 replaced image
        self.assertEqual(images_in_mail, 1)
        # verify 1 attachment present
        self.assertEqual(
            [
                x.get_content_type()
                for x in res.walk()
                if x.get_content_type().startswith("image/")
            ],
            ["image/png"],
        )
