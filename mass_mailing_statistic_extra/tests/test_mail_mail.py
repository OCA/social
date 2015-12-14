# -*- coding: utf-8 -*-
# © 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase
from openerp import fields
from email.utils import formataddr


# One test case per method
class TestResPartner(TransactionCase):

    def test_mail_mail_create(self):
        partner_a = self.env.ref('base.res_partner_address_16')
        partner_b = self.env.ref('base.res_partner_3')
        partner_c = self.env.ref('base.res_partner_2')
        mass_mailing = self.env['mail.mass_mailing'].create({
            'email_from': 'email_from@example.com',
            'name': 'Subject test',
            'mailing_domain': "[['id', 'in', [%d, %d, %d]]]" % (
                partner_a.id,
                partner_b.id,
                partner_c.id
            ),
            'mailing_model': 'res.partner',
            'body_html': '<p>Hello world!</p>',
            'reply_to_mode': 'email',
        })
        mail = self.env['mail.mail'].create({
            'author_id': self.env.ref('base.res_partner_4').id,
            'notification': False,
            'mailing_id': mass_mailing.id,
            'date': fields.Datetime.now(),
            'subject': 'Subject test',
            'email_from': 'email_from@example.com',
            'email_to': partner_a.email,
            'recipient_ids': [
                (4, partner_b.id),
                (4, partner_c.id),
            ],
            'statistics_ids': [(0, 0, {
                'mass_mailing_id': mass_mailing.id,
                'model': 'res.partner',
                'res_id': partner_a.id,
            })],
            'model': 'res.partner',
            'res_id': partner_a.id,
        })

        orig_list = [
            partner_a.email,
            formataddr((partner_b.name, partner_b.email)),
            formataddr((partner_c.name, partner_c.email)),
        ]
        self.assertEqual(len(mail.statistics_ids), 1)
        self.assertEqual(mail.statistics_ids[0].subject, 'Subject test')
        self.assertEqual(mail.statistics_ids[0].email_from,
                         'email_from@example.com')
        for address in mail.statistics_ids[0].email_to.split(';'):
            self.assertIn(address, orig_list)
