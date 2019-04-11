# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import SavepointCase
from odoo import exceptions


class DigestCase(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(DigestCase, cls).setUpClass()
        cls.partner_model = cls.env['res.partner']
        cls.message_model = cls.env['mail.message']
        cls.subtype_model = cls.env['mail.message.subtype']
        cls.digest_model = cls.env['mail.digest']
        cls.conf_model = cls.env['partner.notification.conf']

        cls.partner1 = cls.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 1',
                'email': 'partner1@test.foo.com',
            })
        cls.partner2 = cls.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 2',
                'email': 'partner2@test.foo.com',
            })
        cls.partner3 = cls.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 3',
                'email': 'partner3@test.foo.com',
            })
        cls.subtype1 = cls.subtype_model.create({'name': 'Type 1'})
        cls.subtype2 = cls.subtype_model.create({'name': 'Type 2'})

    def test_get_or_create_digest(self):
        message1 = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        message2 = self.message_model.create({
            'body': 'My Body 2',
            'subtype_id': self.subtype2.id,
        })
        # 2 messages, 1 digest container
        dig1 = self.digest_model._get_or_create_by_partner(
            self.partner1, message1)
        dig2 = self.digest_model._get_or_create_by_partner(
            self.partner1, message2)
        self.assertEqual(dig1, dig2)

    def test_create_or_update_digest(self):
        partners = self.partner_model
        partners |= self.partner1
        partners |= self.partner2
        message1 = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        message2 = self.message_model.create({
            'body': 'My Body 2',
            'subtype_id': self.subtype2.id,
        })
        # partner 1
        self.digest_model.create_or_update(self.partner1, message1)
        self.digest_model.create_or_update(self.partner1, message2)
        p1dig = self.digest_model._get_or_create_by_partner(self.partner1)
        self.assertIn(message1, p1dig.message_ids)
        self.assertIn(message2, p1dig.message_ids)
        # partner 2
        self.digest_model.create_or_update(self.partner2, message1)
        self.digest_model.create_or_update(self.partner2, message2)
        p2dig = self.digest_model._get_or_create_by_partner(self.partner2)
        self.assertIn(message1, p2dig.message_ids)
        self.assertIn(message2, p2dig.message_ids)

    def test_notify_partner_digest(self):
        message = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
        })
        self.partner1.notify_email = 'digest'
        # notify partner
        self.partner1._notify(message)
        # we should find the message in its digest
        dig1 = self.digest_model._get_or_create_by_partner(
            self.partner1, message)
        self.assertIn(message, dig1.message_ids)

    def test_notify_partner_digest_followers(self):
        self.partner3.message_subscribe(self.partner2.ids)
        self.partner1.notify_email = 'digest'
        self.partner2.notify_email = 'digest'
        partners = self.partner1 + self.partner2
        message = self.message_model.create({
            'body': 'My Body 1',
            'subtype_id': self.subtype1.id,
            'res_id': self.partner3.id,
            'model': 'res.partner',
            'partner_ids': [(4, self.partner1.id)]
        })
        # notify partners
        partners._notify(message)
        # we should find the a digest for each partner
        dig1 = self.digest_model._get_by_partner(self.partner1)
        dig2 = self.digest_model._get_by_partner(self.partner2)
        # and the message in them
        self.assertIn(message, dig1.message_ids)
        self.assertIn(message, dig2.message_ids)
        # now we exclude followers
        dig1.unlink()
        dig2.unlink()
        partners.with_context(notify_only_recipients=1)._notify(message)
        # we should find the a digest for each partner
        self.assertTrue(self.digest_model._get_by_partner(self.partner1))
        self.assertFalse(self.digest_model._get_by_partner(self.partner2))

    def test_global_conf(self):
        for k in ('email', 'comment', 'notification'):
            self.assertIn(k, self.partner1._digest_enabled_message_types())
        self.env['ir.config_parameter'].set_param(
            'mail_digest.enabled_message_types',
            'email,notification'
        )
        for k in ('email', 'notification'):
            self.assertIn(k, self.partner1._digest_enabled_message_types())
        self.assertNotIn(
            'comment', self.partner1._digest_enabled_message_types())

    def test_notify_partner_digest_global_disabled(self):
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
        self.partner1.notify_email = 'digest'
        # notify partner
        self.partner1._notify(message)
        # we should not find any digest
        self.assertFalse(self.digest_model._get_by_partner(self.partner1))

    def _create_for_partner(self, partner):
        messages = {}
        for type_id in (self.subtype1.id, self.subtype2.id):
            for k in xrange(1, 3):
                key = '{}_{}'.format(type_id, k)
                messages[key] = self.message_model.create({
                    'subject': 'My Subject {}'.format(key),
                    'body': 'My Body {}'.format(key),
                    'subtype_id': type_id,
                })
                self.digest_model.create_or_update(
                    partner, messages[key])
        return self.digest_model._get_or_create_by_partner(partner)

    def test_digest_group_messages(self):
        dig = self._create_for_partner(self.partner1)
        grouped = dig._message_group_by()
        for type_id in (self.subtype1.id, self.subtype2.id):
            self.assertIn(type_id, grouped)
            self.assertEqual(len(grouped[type_id]), 2)

    def test_digest_mail_values(self):
        dig = self._create_for_partner(self.partner1)
        values = dig._get_email_values()
        expected = ('recipient_ids', 'subject', 'body_html')
        for k in expected:
            self.assertIn(k, values)

        self.assertEqual(self.env.user.company_id.email, values['email_from'])
        self.assertEqual([(4, self.partner1.id)], values['recipient_ids'])

    def test_digest_template(self):
        default = self.env.ref('mail_digest.default_digest_tmpl')
        dig = self._create_for_partner(self.partner1)
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

    def test_digest_message_body_sanitize(self):
        dig = self._create_for_partner(self.partner1)
        message = self.message_model.create({
            'body': '<p style="font-weight:bold">Body!</p>',
            'subtype_id': self.subtype1.id,
            'res_id': self.partner3.id,
            'model': 'res.partner',
            'partner_ids': [(4, self.partner1.id)]
        })
        body = dig.message_body(message)
        self.assertEqual(body, '<p>Body!</p>')

    def test_digest_message_body_no_sanitize(self):
        dig = self._create_for_partner(self.partner1)
        dig.sanitize_msg_body = False
        message = self.message_model.create({
            'body': '<p style="font-weight:bold">Body!</p>',
            'subtype_id': self.subtype1.id,
            'res_id': self.partner3.id,
            'model': 'res.partner',
            'partner_ids': [(4, self.partner1.id)]
        })
        body = dig.message_body(message)
        self.assertEqual(body, '<p style="font-weight:bold">Body!</p>')
