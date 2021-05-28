# Copyright 2020 Camptocamp SA (http://www.camptocamp.com)
# Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import tools
from odoo.tests.common import HttpCase, SavepointCase, tagged


class TestLayoutMixin(object):
    @staticmethod
    def _create_template(env, model, **kw):
        vals = {
            "name": "Test Preview Template",
            "subject": "Preview ${object.name}",
            "body_html": "<p>Hello ${object.name}</p>",
            "model_id": env["ir.model"]._get(model).id,
        }
        vals.update(kw)
        return env["mail.template"].create(vals)


@tagged("-at_install", "post_install")
class TestLayoutPreview(SavepointCase, TestLayoutMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.wiz_model = cls.env["mail.template.preview"]
        cls.partner = cls.env.ref("base.res_partner_4")
        cls.tmpl = cls._create_template(cls.env, cls.partner._name)

    def test_wizard_preview_url(self):
        wiz = self.wiz_model.create(
            {
                "mail_template_id": self.tmpl.id,
                "resource_ref": "{},{}".format(self.partner._name, self.partner.id),
            }
        )
        self.assertEqual(
            wiz.layout_preview_url,
            "/email-preview/res.partner/{}/{}/".format(self.tmpl.id, self.partner.id),
        )


@tagged("-at_install", "post_install")
class TestController(HttpCase, TestLayoutMixin):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        host = "127.0.0.1"
        port = tools.config["http_port"]
        cls.base_url = "http://%s:%d/email-preview/" % (host, port)

    def test_controller1(self):
        self.authenticate("admin", "admin")
        model = "res.partner"
        response = self.url_open(self.base_url + model)
        content = response.content
        tree = etree.fromstring(content)
        list_items = tree.xpath("//ol[@class='email-template-list']/li/a")
        templates = self.env["mail.template"].search([("model_id.model", "=", model)])
        url_pattern = "/email-preview/res.partner/mail.email_template_partner/{}"
        for el, tmpl in zip(list_items, templates):
            self.assertEqual(
                el.attrib, {"class": "preview", "href": url_pattern.format(tmpl.id)}
            )

    def test_controller2(self):
        self.authenticate("admin", "admin")
        partner = self.env.ref("base.res_partner_4")
        model = partner._name
        tmpl = self._create_template(self.env, model)
        response = self.url_open(
            self.base_url + "{}/{}/{}/".format(model, tmpl.id, partner.id)
        )
        content = response.content.decode()
        self.assertIn("<p>Hello {}</p>".format(partner.name), content)
