# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import SavepointCase
from odoo import exceptions


class DigestCase(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(DigestCase, cls).setUpClass()
        cls.message_model = cls.env['mail.message']
        cls.subtype_model = cls.env['mail.message.subtype']
        cls.digest_model = cls.env['mail.digest']
        cls.conf_model = cls.env['user.notification.conf']

        user_model = cls.env['res.users'].with_context(
            no_reset_password=True, tracking_disable=True)
        cls.user1 = user_model.create({
            'name': 'User 1',
            'login': 'testuser1',
            'email': 'testuser1@email.com',
        })
        cls.user2 = user_model.create({
            'name': 'User 2',
            'login': 'testuser2',
            'email': 'testuser2@email.com',
        })
        cls.user3 = user_model.create({
            'name': 'User 3',
            'login': 'testuser3',
            'email': 'testuser3@email.com',
        })
        cls.subtype1 = cls.subtype_model.create({'name': 'Type 1'})
        cls.subtype2 = cls.subtype_model.create({'name': 'Type 2'})

    def test_get_or_create_digest(self):
        self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        self.message_model.create({
            'body': 'My Body 2',
            'subtype_id': self.subtype2.id,
        })
        # 2 messages, 1 digest container
        dig1 = self.digest_model._get_or_create_by_user(self.user1)
        dig2 = self.digest_model._get_or_create_by_user(self.user1)
        self.assertEqual(dig1, dig2)

    def test_create_or_update_digest(self):
        partners = self.env['res.partner']
        partners |= self.user1.partner_id
        partners |= self.user2.partner_id
        message1 = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        message2 = self.message_model.create({
            'body': 'My Body 2',
            'subtype_id': self.subtype2.id,
        })
        # partner 1
        self.digest_model.create_or_update(self.user1.partner_id, message1)
        self.digest_model.create_or_update(self.user1.partner_id, message2)
        p1dig = self.digest_model._get_or_create_by_user(self.user1)
        self.assertIn(message1, p1dig.message_ids)
        self.assertIn(message2, p1dig.message_ids)
        # partner 2
        self.digest_model.create_or_update(self.user2.partner_id, message1)
        self.digest_model.create_or_update(self.user2.partner_id, message2)
        p2dig = self.digest_model._get_or_create_by_user(self.user2)
        self.assertIn(message1, p2dig.message_ids)
        self.assertIn(message2, p2dig.message_ids)

    def test_notify_user_digest(self):
        message = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        self.user1.digest_mode = True
        # notify partner
        self.user1.partner_id._notify(message)
        # we should find the message in its digest
        dig1 = self.digest_model._get_or_create_by_user(self.user1)
        self.assertIn(message, dig1.message_ids)

    def test_notify_partner_digest_followers(self):
        # subscribe a partner to the other one
        self.user3.partner_id.message_subscribe(
            partner_ids=self.user2.partner_id.ids)
        self.user1.digest_mode = True
        self.user2.digest_mode = True
        partners = self.user1.partner_id + self.user2.partner_id
        message = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
            'res_id': self.user3.partner_id.id,
            'model': 'res.partner',
            'partner_ids': [(4, self.user1.partner_id.id)]
        })
        # notify partners
        partners.with_context(foo=1)._notify(message)
        # we should find the a digest for each partner
        dig1 = self.digest_model._get_by_user(self.user1)
        dig2 = self.digest_model._get_by_user(self.user2)
        # and the message in them
        self.assertIn(message, dig1.message_ids)
        self.assertIn(message, dig2.message_ids)
        # now we exclude followers
        dig1.unlink()
        dig2.unlink()
        partners.with_context(notify_only_recipients=True)._notify(message)
        # we should find the a digest for each partner
        self.assertTrue(self.digest_model._get_by_user(self.user1))
        self.assertFalse(self.digest_model._get_by_user(self.user2))

    def test_global_conf(self):
        for k in ('email', 'comment', 'notification'):
            self.assertIn(
                k, self.env['res.partner']._digest_enabled_message_types())
        self.env['ir.config_parameter'].set_param(
            'mail_digest.enabled_message_types',
            'email,notification'
        )
        for k in ('email', 'notification'):
            self.assertIn(
                k, self.env['res.partner']._digest_enabled_message_types())
        self.assertNotIn(
            'comment', self.env['res.partner']._digest_enabled_message_types())

    def test_notify_user_digest_global_disabled(self):
        # change global conf
        self.env['ir.config_parameter'].set_param(
            'mail_digest.enabled_message_types',
            'email,comment'
        )
        message = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
            # globally disabled type
            'message_type': 'notification',
        })
        self.user1.digest_mode = True
        # notify partner
        self.user1.partner_id._notify(message)
        # we should not find any digest
        self.assertFalse(self.digest_model._get_by_user(self.user1))

    def _create_for_partner(self, partner):
        messages = {}
        for type_id in (self.subtype1.id, self.subtype2.id):
            for k in range(1, 3):
                key = '{}_{}'.format(type_id, k)
                messages[key] = self.message_model.create({
                    'subject': 'My Subject {}'.format(key),
                    'body': 'My Body {}'.format(key),
                    'subtype_id': type_id,
                })
                self.digest_model.create_or_update(partner, messages[key])
        return self.digest_model._get_by_user(partner.real_user_id)

    def test_digest_group_messages(self):
        dig = self._create_for_partner(self.user1.partner_id)
        grouped = dig._message_group_by()
        for type_id in (self.subtype1.id, self.subtype2.id):
            self.assertIn(type_id, grouped)
            self.assertEqual(len(grouped[type_id]), 2)

    def test_digest_mail_values(self):
        dig = self._create_for_partner(self.user1.partner_id)
        values = dig._get_email_values()
        expected = ('recipient_ids', 'subject', 'body_html')
        for k in expected:
            self.assertIn(k, values)

        self.assertEqual(self.env.user.company_id.email, values['email_from'])
        self.assertEqual(
            [(4, self.user1.partner_id.id)], values['recipient_ids'])

    def test_digest_template(self):
        default = self.env.ref('mail_digest.default_digest_tmpl')
        dig = self._create_for_partner(self.user1.partner_id)
        # check default
        self.assertEqual(dig.digest_template_id, default)
        self.assertTrue(dig._get_email_values())
        # drop template
        dig.digest_template_id = False
        # pass a custom one: ok
        self.assertTrue(dig._get_email_values(template=default))
        # raise error if no template found
        with self.assertRaises(exceptions.UserError):
            dig._get_email_values()
