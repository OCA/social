# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestMessageSecurityAuthor(TransactionCase):

    def setUp(self):
        super(TestMessageSecurityAuthor, self).setUp()
        self.partner_obj = self.env['res.partner']
        self.user_obj = self.env['res.users']
        self.message_obj = self.env['mail.message']
        employee_group = self.env.ref('base.group_user')
        partner_manager_group = self.env.ref('base.group_partner_manager')
        message_manager_group = self.env.ref(
            'message_security_author.group_mail_message_manager')

        self.user1 = self.user_obj.with_context(
            no_reset_password=True).create({
                'name': 'user 1',
                'login': 'test_user_1',
                'email': 'user1@example.com',
                'groups_id': [(6, 0, [
                    employee_group.id, partner_manager_group.id,
                    message_manager_group.id,
                ])],
            })
        self.user2 = self.user_obj.with_context(
            no_reset_password=True).create({
                'name': 'user2',
                'login': 'test_user_2',
                'email': 'user2@example.com',
                'groups_id': [(6, 0, [
                    employee_group.id, partner_manager_group.id,
                ])],
            })

        self.partner = self.partner_obj.create({
            'name': 'Ugly contact',
        })

        self.partner.sudo(self.user1).with_context(
            mail_notrack=True).message_post(
            body='I think you are ugly',
            subtype='mail.mt_comment',
            message_type='comment',
        )

        self.message_user_1 = self.message_obj.search(
            [('body', '=', 'I think you are ugly'),
             ('model', '=', 'res.partner'),
             ('res_id', '=', self.partner.id)], limit=1)

        self.partner.sudo(self.user2).with_context(
            mail_notrack=True).message_post(
            body='Me too haha',
            subtype='mail.mt_comment',
            message_type='comment',
        )

        self.message_user_2 = self.message_obj.search(
            [('body', '=', 'Me too haha'), ('model', '=', 'res.partner'),
             ('res_id', '=', self.partner.id)], limit=1)

    def test_user1_manipulate_message(self):
        self.message_user_1.sudo(self.user1).write({'body': 'sorry'})
        self.assertIn('sorry', self.message_user_1.body)
        self.message_user_2.sudo(self.user1).write({'body': 'wtf'})
        self.assertIn('wtf', self.message_user_2.body)
        self.message_user_1.sudo(self.user1).unlink()
        self.assertFalse(self.message_user_1.exists().id)
        self.message_user_2.sudo(self.user1).unlink()
        self.assertFalse(self.message_user_2.exists().id)
        self.assertTrue(self.partner.exists().id)

    def test_user1_delete_partner(self):
        self.partner.sudo(self.user1).unlink()
        self.assertFalse(self.message_user_1.exists().id)
        self.assertFalse(self.message_user_2.exists().id)

    def test_user2_manipulate_message(self):
        with self.assertRaises(AccessError):
            self.message_user_1.sudo(self.user2).write({'body': 'sorry'})
        self.message_user_2.sudo(self.user2).write({'body': 'wtf'})
        self.assertIn('wtf', self.message_user_2.body)
        with self.assertRaises(AccessError):
            self.message_user_1.sudo(self.user2).unlink()
        self.message_user_2.sudo(self.user2).unlink()
        self.assertFalse(self.message_user_2.exists().id)
        self.assertTrue(self.partner.exists().id)

    def test_user2_delete_partner(self):
        self.partner.sudo(self.user2).unlink()
        self.assertFalse(self.message_user_1.exists().id)
        self.assertFalse(self.message_user_2.exists().id)
