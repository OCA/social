# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import html

from odoo.tests import TransactionCase


class TestMailInlineStyles(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_template = cls.env.ref("mail_inline_css.email_template_demo")
        cls.demo_user = cls.env.ref("base.user_demo")

    def to_xml_node(self, html_):
        return html.fragments_fromstring(html_)

    def parse_node_style(self, node):
        """Convert node CSS string to Python dict"""
        res = {}
        for style in node.attrib.get("style", "").split(";"):
            rule = style.split(":")
            res[rule[0].strip()] = rule[1].strip()
        return res

    def find_by_id(self, node, html_id):
        return node.xpath(f'//*[@id="{html_id}"]')

    def assertNodeStyle(self, node, expected):
        self.assertIn("style", node.attrib)
        self.assertEqual(self.parse_node_style(node), expected)

    def test_generate_mail(self):
        res = self.mail_template._generate_template(
            [self.demo_user.id], render_fields=["body_html"]
        )
        body_html_string = res[self.demo_user.id].get("body_html")
        html_node = self.to_xml_node(body_html_string)[0]

        expected = {
            "main_logo": {"max-width": "300px"},
            "main_wrapper": {
                "max-width": "620px",
                "margin": "0 auto",
                "border": "1px solid #ccc",
                "font-size": "18px",
                "font-family": "verdana",
                "color": "#6B6E71",
            },
            "main_footer": {
                "padding-top": "0",
                "font-size": "120%",
                "padding": "30px 40px",
            },
        }

        for html_id, expected_style in expected.items():
            node = self.find_by_id(html_node, html_id)[0]
            self.assertNodeStyle(node, expected_style)
