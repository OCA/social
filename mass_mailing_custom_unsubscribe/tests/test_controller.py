# -*- coding: utf-8 -*-
# © 2016 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock
from contextlib import contextmanager

from openerp.tests.common import TransactionCase

from openerp.addons.mass_mailing_custom_unsubscribe.controllers.main import (
    CustomUnsubscribe
)


model = 'openerp.addons.mass_mailing_custom_unsubscribe.controllers.main'


@contextmanager
def mock_assets():
    """ Mock & yield controller assets """
    with mock.patch('%s.request' % model) as request:
        yield {
            'request': request,
        }


class EndTestException(Exception):
    pass


class TestController(TransactionCase):

    def setUp(self):
        super(TestController, self).setUp()
        self.controller = CustomUnsubscribe()

    def _default_domain(self):
        return [
            ('opt_out', '=', False),
            ('list_id.not_cross_unsubscriptable', '=', False),
        ]

    def test_mailing_list_contacts_by_email_search(self):
        """ It should search for contacts """
        expect = 'email'
        with mock_assets() as mk:
            self.controller._mailing_list_contacts_by_email(expect)
            model_obj = mk['request'].env['mail.mass_mailing.contact'].sudo()
            model_obj.search.assert_called_once_with(
                [('email', '=', expect)] + self._default_domain()
            )

    def test_mailing_list_contacts_by_email_return(self):
        """ It should return result of search """
        expect = 'email'
        with mock_assets() as mk:
            res = self.controller._mailing_list_contacts_by_email(expect)
            model_obj = mk['request'].env['mail.mass_mailing.contact'].sudo()
            self.assertEqual(
                model_obj.search(), res,
            )

    def test_unsubscription_reason_gets_context(self):
        """ It should retrieve unsub qcontext """
        expect = 'mailing_id', 'email', 'res_id', 'token'
        with mock_assets():
            with mock.patch.object(
                self.controller, 'unsubscription_qcontext'
            ) as unsub:
                unsub.side_effect = EndTestException
                with self.assertRaises(EndTestException):
                    self.controller.unsubscription_reason(*expect)
                unsub.assert_called_once_with(*expect)

    def test_unsubscription_updates_with_extra_context(self):
        """ It should update qcontext with provided vals """
        expect = 'mailing_id', 'email', 'res_id', 'token'
        qcontext = {'context': 'test'}
        with mock_assets():
            with mock.patch.object(
                self.controller, 'unsubscription_qcontext'
            ) as unsub:
                self.controller.unsubscription_reason(
                    *expect, qcontext_extra=qcontext
                )
                unsub().update.assert_called_once_with(qcontext)

    def test_unsubscription_updates_rendered_correctly(self):
        """ It should correctly render website """
        expect = 'mailing_id', 'email', 'res_id', 'token'
        with mock_assets() as mk:
            with mock.patch.object(
                self.controller, 'unsubscription_qcontext'
            ) as unsub:
                self.controller.unsubscription_reason(*expect)
                mk['request'].website.render.assert_called_once_with(
                    "mass_mailing_custom_unsubscribe.reason_form",
                    unsub(),
                )

    def test_unsubscription_updates_returns_site(self):
        """ It should return website """
        expect = 'mailing_id', 'email', 'res_id', 'token'
        with mock_assets() as mk:
            with mock.patch.object(
                self.controller, 'unsubscription_qcontext'
            ):
                res = self.controller.unsubscription_reason(*expect)
                self.assertEqual(
                    mk['request'].website.render(), res
                )
