# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields
from openerp.tests.common import TransactionCase


class TestMailActivity(TransactionCase):
    def test_mail_activity(self):
        partner = self.env.ref('base.res_partner_address_1')
        activity = self.env['mail.activity'].with_context(
            default_res_model=partner._name,
        ).create({
            'res_id': partner.id,
            'activity_type_id': self.env.ref(
                'mail_activity.mail_activity_data_meeting',
            ).id,
            'date_deadline': fields.Date.today(),
            'summary': 'Hello world',
        })
        self.assertEqual(activity.res_name, partner.display_name)
        self.assertEqual(activity.state, 'today')
        self.assertEqual(partner.activity_state, 'today')
        activity.write({'user_id': self.env.ref('base.user_demo').id})
        self.assertIn(
            partner,
            self.env['res.partner'].search([
                ('activity_user_id', '=', activity.user_id.id),
            ])
        )
        self.assertIn(
            partner,
            self.env['res.partner'].search([
                ('activity_summary', 'like', 'Hello world'),
            ])
        )
        activity.action_feedback('feedback')
        self.assertIn('feedback', partner.message_ids[:1].body)
        self.assertFalse(activity.exists())
        partner.unlink()
        self.assertFalse(self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner.id),
        ]))
