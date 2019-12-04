# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from base64 import b64encode
from odoo.tests import common
from mock import patch
from lxml import html
from requests import get
from odoo import api, registry, SUPERUSER_ID


class TestMailEmbedImage(common.TransactionCase):

    post_install = True
    at_install = False

    @patch(
        'odoo.fields.html_sanitize',
        side_effect=lambda *args, **kwargs: args[0],
    )
    def test_mail_embed_image(self, html_sanitize):
        """ The following are tested here:
        1) Create an email with no image, send it.
        2) Create an email with three images, one base64 content, one http
        full url and one of the format `/web/image/.*`

        We assert that nothing has changed on 1) and only the `/web/image/.*`
        has changed in 2)
        """
        reg = registry(common.get_db_name())
        env = api.Environment(reg.cursor(), SUPERUSER_ID, {})
        # DATA
        model_ir_mail_server = env['ir.mail_server']
        model_mail_mail = self.env['mail.mail']
        base_url = self.env['ir.config_parameter'].get_param(
            'web.base.url')
        image_url = base_url + \
            '/mail_embed_image/static/description/icon.png'
        image = get(image_url).content
        body1 = '<div>this is an email</div>'
        email1 = model_mail_mail.create({
            'body_html': body1,
            'email_from': 'test@example.com',
            'email_to': 'test@example.com',
            'mail_server_id': self.env['ir.mail_server'].search(
                [], limit=1).id,
        })
        body2 = html.tostring(html.fromstring("""
            <div>
            this is an email
            <img src="base64: %s"></img>
            <img src="%s"></img>
            <img src="%s"></img>
            </div>""" % (
            b64encode(image),
            image_url,
            '/web/image/res.partner/1/image',
            )))
        email2 = model_mail_mail.create({
            'body_html': body2,
            'email_from': 'test@example.com',
            'email_to': 'test@example.com',
            'mail_server_id': self.env['ir.mail_server'].search(
                [], limit=1).id,
        })
        # END DATA
        with patch.object(
                env['ir.mail_server'].__class__, 'build_email'
                ) as mock_build_email:
            email1.send()
            mock_build_email.assert_called()
            self.assertIn(
                body1,
                mock_build_email.call_args[1].get(
                    'body') or model_ir_mail_server.mock_build_email.call_args[
                        0][3])
        with patch.object(
                env['ir.mail_server'].__class__, 'send_email'
                ) as mock_send_email:
            email1.send()
            self.assertIn(
                body1,
                model_ir_mail_server.send_email.call_args[0][0].get_payload(
                    )[0].get_payload()[1].get_payload(decode=True),
            )
            email2.send()
            mock_send_email.assert_called()
            self.assertIn(
                'img src="cid:',
                mock_send_email.call_args[0][0].get_payload(
                    )[0].get_payload()[1].get_payload(decode=True),
            )
