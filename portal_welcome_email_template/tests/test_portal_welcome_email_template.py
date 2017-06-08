# -*- coding: utf-8 -*-
# (c) 2015 Incaser Informatica S.L. - Sergio Teruel
# (c) 2015 Incaser Informatica S.L. - Carlos Dauden
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from openerp.tests.common import TransactionCase


class TestWelcomeEmailTemplate(TransactionCase):

    def setUp(self):
        super(TestWelcomeEmailTemplate, self).setUp()
        partner_obj = self.env['res.partner']
        self.partner = partner_obj.create({
            'name': 'partner_test',
            'email': 'test@example.com',
        })

        self.wiz_portal_access = self.env['portal.wizard'].create({
            'user_ids': [(0, 0, {
                'partner_id': self.partner.id,
                'email': self.partner.email,
                'in_portal': True,
            })],
        })

    def test_send_mail(self):
        self.wiz_portal_access.user_ids.action_apply()
        portal_user = self.env['res.users'].search(
            [('partner_id', '=', self.partner.id)])
        self.assertTrue(portal_user)
        mail = self.env['mail.mail'].search([
            ('model', '=', 'res.users'),
            ('res_id', '=', portal_user.id)
        ])
        self.assertTrue(mail)
