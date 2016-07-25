# -*- coding: utf-8 -*-
# © 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock

from openerp.tests.common import TransactionCase


model = 'openerp.addons.mass_mailing_custom_unsubscribe.models.mail_mail'


class EndTestException(Exception):
    pass


class TestMailMail(TransactionCase):

    def setUp(self):
        super(TestMailMail, self).setUp()
        self.Model = self.env['mail.mail']
        param_obj = self.env['ir.config_parameter']
        self.base_url = param_obj.get_param('web.base.url')
        self.config_msg = param_obj.get_param(
            'mass_mailing.unsubscribe.label'
        )

    @mock.patch('%s.urlparse' % model)
    @mock.patch('%s.urllib' % model)
    def test_get_unsubscribe_url_proper_url(self, urllib, urlparse):
        """ It should join the URL w/ proper args """
        urlparse.urljoin.side_effect = EndTestException
        expect = mock.MagicMock(), 'email', 'msg'
        with self.assertRaises(EndTestException):
            self.Model._get_unsubscribe_url(*expect)
        urlparse.urljoin.assert_called_once_with(
            self.base_url,
            'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': expect[0].mailing_id.id,
                'params': urllib.urlencode(),
            }
        )

    @mock.patch('%s.urlparse' % model)
    @mock.patch('%s.urllib' % model)
    def test_get_unsubscribe_url_correct_params(self, urllib, urlparse):
        """ It should create URL params w/ proper data """
        urlparse.urljoin.side_effect = EndTestException
        expect = mock.MagicMock(), 'email', 'msg'
        with self.assertRaises(EndTestException):
            self.Model._get_unsubscribe_url(*expect)
        urllib.urlencode.assert_called_once_with(dict(
            db=self.env.cr.dbname,
            res_id=expect[0].res_id,
            email=expect[1],
            token=self.env['mail.mass_mailing'].hash_create(
                expect[0].mailing_id.id,
                expect[0].res_id,
                expect[1],
            )
        ))

    @mock.patch('%s.urlparse' % model)
    @mock.patch('%s.urllib' % model)
    def test_get_unsubscribe_url_false_config_msg(self, urllib, urlparse):
        """ It should return default config msg when none supplied """
        expects = ['uri', False]
        urlparse.urljoin.return_value = expects[0]
        with mock.patch.object(self.Model, 'env') as env:
            env['ir.config_paramater'].get_param.side_effect = expects
            res = self.Model._get_unsubscribe_url(
                mock.MagicMock(), 'email', 'msg'
            )
            self.assertIn(
                expects[0], res,
                'Did not include URI in default message'
            )
            self.assertIn(
                'msg', res,
                'Did not include input msg in default message'
            )

    @mock.patch('%s.urlparse' % model)
    @mock.patch('%s.urllib' % model)
    def test_get_unsubscribe_url_with_config_msg(self, urllib, urlparse):
        """ It should return config message w/ URL formatted """
        expects = ['uri', 'test %(url)s']
        urlparse.urljoin.return_value = expects[0]
        with mock.patch.object(self.Model, 'env') as env:
            env['ir.config_paramater'].get_param.side_effect = expects
            res = self.Model._get_unsubscribe_url(
                mock.MagicMock(), 'email', 'msg'
            )
            self.assertEqual(
                expects[1] % {'url': expects[0]}, res,
                'Did not return proper config message'
            )
