# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree
from openerp.tests.common import TransactionCase


class TestMailRestrictFollowerSelection(TransactionCase):

    def test_fields_view_get(self):
        result = self.env['mail.wizard.invite'].fields_view_get(
            view_type='form')
        for field in etree.fromstring(result['arch']).xpath(
                '//field[@name="partner_ids"]'):
            self.assertTrue(field.get('domain'))
