# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo.models import SUPERUSER_ID


class TestCreator(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({
            'name': 'DEMO'
        })
        self.user_01 = self.env['res.users'].create({
            'name': 'user_01',
            'login': 'demo_user_01',
            'email': 'demo@demo.de',
            'notification_type': 'inbox',
        })
        self.model_id = self.env['ir.model']._get('res.partner').id
        self.activity_type = self.env['mail.activity.type'].create({
            'name': 'Initial Contact',
            'days': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model_id': self.model_id,
        })

    def test_activity_creator(self):
        activity = self.env['mail.activity'].sudo(self.user_01.id).create({
            'activity_type_id': self.activity_type.id,
            'note': 'Partner activity 3.',
            'res_id': self.partner.id,
            'res_model_id': self.model_id,
            'user_id': self.user_01.id
        })
        self.assertEqual(activity.creator_uid, self.user_01)
        self.assertEqual(activity.create_uid.id, SUPERUSER_ID)
