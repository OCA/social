# Copyright (C) 2015 Therp BV <http://therp.nl>
# Copyright (C) 2017 Komit <http://www.komit-consulting.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import etree
from odoo.tests.common import TransactionCase


class TestMailRestrictFollowerSelection(TransactionCase):

    def setUp(self):
        super().setUp()
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
        compose.action_send_mail()

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
