# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from lxml import etree
from odoo.tests.common import TransactionCase


class TestMailRestrictFollowerSelection(TransactionCase):

    def setUp(self):
        super(TestMailRestrictFollowerSelection, self).setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'Partner',
            'customer': True,
            'email': 'test@test.com',
        })

    def test_fields_view_get(self):
        result = self.env['mail.wizard.invite'].fields_view_get(
            view_type='form')
        for field in etree.fromstring(result['arch']).xpath(
                '//field[@name="partner_ids"]'):
            self.assertTrue(field.get('domain'))

    def send_action(self):
        compose = self.env['mail.compose.message'].with_context({
            'mail_post_autofollow': True,
            'default_composition_mode': 'comment',
            'default_model': 'res.partner',
            'default_use_active_domain': True,
        }).create({
            'subject': 'From Composer Test',
            'body': '${object.description}',
            'res_id': self.partner.id,
            'partner_ids': [(4, id) for id in self.partner.ids],
        })
        self.assertEqual(compose.partner_ids, self.partner)
        compose.send_mail_action()

    def test_followers_meet(self):
        self.partner.write({'customer': True})
        self.assertTrue(self.partner.customer)
        self.send_action()
        self.assertIn(
            self.partner,
            self.partner.message_follower_ids.mapped('partner_id')
        )

    def test_followers_not_meet(self):
        self.partner.write({'customer': False})
        self.assertFalse(self.partner.customer)
        self.send_action()
        self.assertNotIn(
            self.partner,
            self.partner.message_follower_ids.mapped('partner_id')
        )
