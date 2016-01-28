# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import openerp.tests.common as common


class TestMailNotification(common.TransactionCase):

    def setUp(self):
        super(TestMailNotification, self).setUp()

        self.mail_notification_obj = self.env['mail.notification']
        self.partner_obj = self.env['res.partner']

        self.registry('ir.model').clear_caches()
        self.registry('ir.model.data').clear_caches()

    def test_get_signature_footer(self):

        vals = {
            'name': 'p1@exemple.com',
            'notify_email': 'none',
        }
        partner1 = self.partner_obj.create(vals)
        vals = {
            'name': 'p2@exemple.com',
            'notify_email': 'always',
        }
        partner2 = self.partner_obj.create(vals)
        footer = self.mail_notification_obj.get_signature_footer(self.env.uid)
        self.assertFalse(
            partner1.name in footer or partner2.name in footer,
            'Standard behavior does not add notified partners into the footer')

        footer = self.mail_notification_obj.with_context(
            partners_to_notify=[partner1.id, partner2.id]
        ).get_signature_footer(self.env.uid)

        self.assertFalse(
            partner1.name in footer,
            'Partner with "notify_email: "none" should not be into the footer')
        self.assertTrue(
            partner2.name in footer,
            'Partner with "notify_email: "always" should be into the footer')
