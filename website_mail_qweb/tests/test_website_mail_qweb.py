# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import HttpCase
from ..controllers.main import UnquoteObject


class TestWebsiteMailQweb(HttpCase):
    def test_website_mail_qweb(self):
        self.authenticate('admin', 'admin')
        result = self.url_open(
            '/website_mail/email_designer?model=email.template&res_id=%s' %
            self.env.ref('email_template_qweb.email_template_demo1').id
        )
        self.assertIn('Dear object.name,', result.read())

    def test_unquote_object(self):
        self.assertEqual(UnquoteObject('hello.world'), "hello.world")
        self.assertEqual(
            UnquoteObject('hello.world(42).test'), "hello.world(42).test"
        )
        self.assertEqual(
            UnquoteObject("hello.world(42, hello='42').test"),
            "hello.world(42, hello='42').test"
        )
        self.assertEqual(
            UnquoteObject('hello.world[42].test'), "hello.world[42].test"
        )
