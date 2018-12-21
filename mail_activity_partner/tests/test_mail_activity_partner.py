# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestMailActivityPartner(TransactionCase):

    def setUp(self):
        super(TestMailActivityPartner, self).setUp()

        self.user_admin = self.env.ref('base.user_root')

        self.employee = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Employee",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('base.group_partner_manager').id])]
        })

        self.partner_ir_model = self.env['ir.model']._get('res.partner')

        activity_type_model = self.env['mail.activity.type']
        self.activity1 = activity_type_model.create({
            'name': 'Initial Contact',
            'days': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model_id': self.partner_ir_model.id,
        })
        self.activity2 = activity_type_model.create({
            'name': 'Call for Demo',
            'days': 6,
            'summary': 'ACT 2 : I want to show you my ERP !',
            'res_model_id': self.partner_ir_model.id,
        })

        self.partner_01 = self.env.ref('base.res_partner_1')

        self.homer = self.env['res.partner'].create({
            'name': 'Homer Simpson',
            'city': 'Springfield',
            'street': '742 Evergreen Terrace',
            'street2': 'Donut Lane',
            'street3': 'Tho',
        })

        # test synchro of street3 on create
        self.partner_10 = self.env['res.partner'].create({
            'name': 'Bart Simpson',
            'parent_id': self.homer.id,
            'type': 'contact',
        })

    def test_partner_for_activity(self):

        self.act1 = self.env['mail.activity'].sudo().create({
            'activity_type_id': self.activity1.id,
            'note': 'Partner activity 1.',
            'res_id': self.partner_01.id,
            'res_model_id': self.partner_ir_model.id,
            'user_id': self.user_admin.id,
        })

        self.act2 = self.env['mail.activity'].sudo(self.employee).create({
            'activity_type_id': self.activity2.id,
            'note': 'Partner activity 10.',
            'res_id': self.partner_10.id,
            'res_model_id': self.partner_ir_model.id,
            'user_id': self.employee.id,
        })

        # Check partner_id of created activities
        self.assertEqual(self.act1.partner_id, self.partner_01)
        self.assertEqual(self.act2.partner_id, self.partner_10)

        # Check commercial_partner_id for created activities
        self.assertEqual(self.act1.commercial_partner_id, self.partner_01)
        self.assertEqual(self.act2.commercial_partner_id, self.homer)
