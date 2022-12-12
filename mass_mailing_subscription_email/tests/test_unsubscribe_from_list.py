# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import MockEmail


@tagged("-at_install", "post_install")
class WebsiteSaleHttpCase(HttpCase, MockEmail):
    def setUp(self):
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tracking_disable=True))
        self.mailing_list = self.env.ref("mass_mailing.mailing_list_data")
        self.mailing_contact = self.env["mailing.contact"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
            }
        )

    def test_subscription_email_unsubscribe_from_list(self):
        # Create subscription
        with self.mock_mail_gateway():
            subs = self.env["mailing.contact.subscription"].create(
                {
                    "contact_id": self.mailing_contact.id,
                    "list_id": self.mailing_list.id,
                }
            )
        body = self._new_mails._send_prepare_values()["body"]
        root = etree.fromstring(body, etree.HTMLParser())
        anchor = root.xpath("//a[@href]")[0]
        unsubscribe_url = anchor.attrib["href"]
        web_base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        self.url_open(unsubscribe_url.replace(web_base_url, ""))
        subs.invalidate_cache()
        self.assertEqual(subs.opt_out, True)
