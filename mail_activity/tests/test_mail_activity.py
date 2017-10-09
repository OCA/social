# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields
from openerp.tests.common import TransactionCase


class TestMailActivity(TransactionCase):
    def test_mail_activity(self):
        partner = self.env['res.partner'].search([], limit=1)
        activity = self.env['mail.activity'].with_context(
            default_res_model=partner._name,
        ).create({
            'res_id': partner.id,
            'activity_type_id': self.env.ref(
                'mail_activity.mail_activity_data_meeting',
            ).id,
            'date_deadline': fields.Date.today(),
        })
        self.assertEqual(activity.res_name, partner.display_name)
        self.assertEqual(activity.state, 'today')
        self.assertEqual(partner.activity_state, 'today')
        activity.write({'user_id': self.env.ref('base.user_demo').id})
        activity.action_feedback('feedback')
        self.assertIn('feedback', partner.message_ids[:1].body)
        self.assertFalse(activity.exists())
