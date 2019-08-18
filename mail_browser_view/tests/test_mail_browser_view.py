# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase
from odoo import fields
from base64 import urlsafe_b64encode
from datetime import datetime
from lxml import html
from werkzeug.urls import url_parse
from ..controllers.browser_view import EmailBrowserViewController
from mock import patch


class MailBrowserView(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(MailBrowserView, cls).setUpClass()
        cls.mail = cls.env['mail.mail']
        cls.mail0 = cls.env.ref('mail_browser_view.browser_view_demo')
        cls.valid_token = cls.mail0.view_in_browser_url.split('/')[-1]

    def _forge_token(self, access_token, rec_id):
        return urlsafe_b64encode(
            (access_token + str(rec_id)).encode()
        ).decode()

    def _test_token(self, token, expected_result):
        rec = self.mail.get_record_for_token(token)
        self.assertEqual(rec, expected_result)

    def test_mail_browser_view(self):
        self._test_token(self.valid_token, self.mail0)

    def test_invalid_b64(self):
        self._test_token(self.valid_token[::2], self.mail)

    def test_invalid_access_token(self):
        bad_token = self._forge_token('0000000', self.mail0.id)
        self._test_token(bad_token, self.mail)

    def test_nonexistent_id(self):
        bad_token = self._forge_token(self.mail0.access_token, 999999)
        self._test_token(bad_token, self.mail)

    def test_token_expiration(self):
        self.mail0.mail_message_id.date = fields.Datetime.to_string(
            datetime.fromtimestamp(0)
        )
        self._test_token(self.valid_token, self.mail)

        self.env.ref('mail_browser_view.token_expiration_hours').value = '0'
        self.mail0.refresh()
        self._test_token(self.valid_token, self.mail0)

    def test_html_render(self):
        html_node = html.fromstring(self.mail0.body_html)
        link_node = html_node.xpath("//a[hasclass('view_in_browser_url')]")
        self.assertEqual(
            url_parse(link_node[0].get('href')).path,
            self.mail0.view_in_browser_url
        )

        self.mail0.auto_delete = True
        self.mail0._replace_view_url()
        self.mail0.refresh()
        html_node = html.fromstring(self.mail0.body_html)

        link_node = html_node.xpath("//a[hasclass('view_in_browser_url')]")
        self.assertEqual(link_node, [])

        link_node = html_node.xpath(
            "//a[not(hasclass('view_in_browser_url'))]"
        )
        self.assertEqual(len(link_node), 1)
        self.assertEqual(link_node[0].get('href'), 'https://www.google.com')

        p_node = html_node.xpath("//p")
        self.assertEqual(len(p_node), 2)

    @patch('odoo.addons.mail_browser_view.'
           'controllers.browser_view.request')
    def test_controller(self, req):
        # Mock
        req.env = self.env
        controller = EmailBrowserViewController()

        controller.email_view(self.valid_token[::2])
        req.not_found.assert_called_once_with()
        req.make_response.assert_not_called()
        req.reset_mock()

        controller.email_view(self.valid_token)
        req.not_found.assert_not_called()
        req.make_response.assert_called_with(self.mail0.body_html)
