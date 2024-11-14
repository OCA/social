# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64

from lxml import html
from requests import get

from odoo.tests import common


class TestMailEmbedImage(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestMailEmbedImage, cls).setUpClass()
        cls.company = cls.env.ref("base.main_company")
        base_url = cls.env["ir.config_parameter"].get_param("web.base.url")
        cls.image_url = base_url + "/mail_embed_image/static/description/icon.png"
        cls.image_content = get(cls.image_url, timeout=10).content
        cls.email_from = "test@example.com"
        cls.email_to = "test@example.com"
        cls.subject = "test mail"

    def build_email(self, option="cid"):
        """Build an email with a given embedding option

        option -- the embedding option to use according to the company setting
        """
        self.company.image_embedding_method = option
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
                    base64.b64encode(self.image_content).decode("utf-8"),
                    # dito, not uploaded content
                    self.image_url,
                )
            )
        )
        return self.env["ir.mail_server"].build_email(
            self.email_from,
            [self.email_to],
            self.subject,
            body,
            subtype="html",
            subtype_alternative="plain",
        )

    def test_mail_embed_image_option_none(self):
        """No embedding option

        We pass a mail with <img src="..." /> tags to build_email,
        and then look into the result, check there no changes were made"""
        res = self.build_email("none")
        images_in_mail = 0
        for part in res.walk():
            if part.get_content_type() == "text/html":
                # we do not search in text, just in case that texts exists in
                # the text elsewhere (not probable, but this is better)
                images_in_mail += len(
                    html.fromstring(part.get_payload(decode=True)).xpath(
                        "//img[starts-with(@src, 'data:image/png;base64,')]"
                    )
                )
                images_in_mail += len(
                    html.fromstring(part.get_payload(decode=True)).xpath(
                        "//img[starts-with(@src, 'cid:')]"
                    )
                )
        # verify 0 replaced images
        self.assertEqual(images_in_mail, 0)
        # verify 0 attachment present
        self.assertEqual(
            [
                x.get_content_type()
                for x in res.walk()
                if x.get_content_type().startswith("image/")
            ],
            [],
        )

    def test_mail_embed_image_option_cids(self):
        """CIDs attachement option

        We pass a mail with <img src="..." /> tags to build_email,
        and then look into the result, check there were attachments
        created and you find xpaths like //img[src] have a cid"""
        res = self.build_email("cid")
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

    def test_mail_embed_image_option_data(self):
        """Data URL option

        We pass a mail with <img src="..." /> tags to build_email,
        and then look into the result, check there were attachments
        created and you find xpaths like //img[src] have a data URL"""
        res = self.build_email("data")
        images_in_mail = 0
        for part in res.walk():
            if part.get_content_type() == "text/html":
                # we do not search in text, just in case that texts exists in
                # the text elsewhere (not probable, but this is better)
                images_in_mail += len(
                    html.fromstring(part.get_payload(decode=True)).xpath(
                        "//img[starts-with(@src, 'data:image/png;base64,')]"
                    )
                )
        # verify 2 replaced image
        self.assertEqual(images_in_mail, 1)
        # verify 0 attachment present
        self.assertEqual(
            [
                x.get_content_type()
                for x in res.walk()
                if x.get_content_type().startswith("image/")
            ],
            [],
        )
