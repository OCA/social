# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tests.common import HttpCase
from ..controllers.main import UnquoteRecordset


class TestWebsiteMailQweb(HttpCase):
    def test_website_mail_qweb(self):
        self.authenticate('admin', 'admin')
        result = self.url_open(
            '/website_mail/email_designer?model=email.template&res_id=%s' %
            self.env.ref('email_template_qweb.email_template_demo1').id
        )
        self.assertIn('Dear object.name,', result.read())

    def test_unquote_recordset(self):
        record = UnquoteRecordset(self.env['res.partner'].new(), 'object')
        self.assertEqual(record.name, 'object.name')
        self.assertEqual(record.parent_id.name, 'object.parent_id.name')
