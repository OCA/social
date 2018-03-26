# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.tests.common import TransactionCase


class TestMailRestrictAutomaticFollower(TransactionCase):

    def setUp(self):
        super(TestMailRestrictAutomaticFollower, self).setUp()
        self.param = self.env.ref(
            'mail_restrict_auto_follower.parameter_domain')
        # This group will be used for testing as it inherits from mail.thread
        self.mail_group_model = self.env['mail.group']
        # Make sure the param has the correct value
        self.param_value = "[('user_ids', '!=', False)]"
        self.param.write({'value': self.param_value})
        self.group = self.mail_group_model.create(
            {'name': 'Test group',
             'public': 'private'})
        self.partner = self.env.ref('base.res_partner_1')

    def test_domain(self):
        # Test global domain
        domain = self.mail_group_model._mail_restrict_follower_get_domain()
        self.assertEqual(domain, self.param_value)
        # Test model domain
        new_domain = "[('employee', '=', 1)]"
        self.env['ir.config_parameter'].create(
            {'key': 'mail_restrict_auto_follower.domain.mail.group',
             'value': new_domain})
        domain = self.mail_group_model._mail_restrict_follower_get_domain()
        self.assertEqual(domain, new_domain)

    def test_auto_subscribe(self):
        # Clear followers list
        self.group.message_unsubscribe(self.group.message_follower_ids.ids)
        self.group.message_subscribe(self.partner.ids)
        self.assertEqual(len(self.group.message_follower_ids), 0)
        self.group.message_subscribe(self.env.user.partner_id.ids)
        self.assertEqual(len(self.group.message_follower_ids), 1)

    def test_wizard_invite(self):
        wizard = self.env["mail.wizard.invite"].create(
            {'res_model': 'mail.group',
             'res_id': self.group.id,
             'partner_ids': [(6, 0, self.partner.ids)],
             'send_mail': False})
        wizard.add_followers()
        self.assertTrue(self.partner.id in self.group.message_follower_ids.ids)
