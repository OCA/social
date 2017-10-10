# -*- coding: utf-8 -*-
# © 2016 ACSONE SA/NV <https://acsone.eu>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common


class TestMailNotification(common.TransactionCase):
    def setUp(self):
        super(TestMailNotification, self).setUp()

        self.partner_obj = self.env['res.partner']

    def test_get_signature_footer(self):
        vals = {
            'name': 'p1@example.com',
        }
        partner1 = self.partner_obj.create(vals)

        body = 'this is the body'
        subject = 'this is the subject'
        recipients = partner1
        emails, recipients_nbr = \
            self.partner_obj._notify_send(body, subject, recipients)

        self.assertTrue(
            partner1.name in emails.body_html,
            'Partner name is not in the body of the mail')
