# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestMailActivityDoneMethods(TransactionCase):

    def setUp(self):
        super(TestMailActivityDoneMethods, self).setUp()

        self.employee = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Test User",
            'login': "testuser",
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        activity_type = self.env['mail.activity.type'].search(
            [('name', '=', 'Meeting')], limit=1)
        self.act1 = self.env['mail.activity'].create({
            'activity_type_id': activity_type.id,
            'res_id': self.env.ref("base.res_partner_1").id,
            'res_model_id': self.env['ir.model']._get('res.partner').id,
            'user_id': self.employee.id,
        })

    def test_mail_activity_done(self):
        self.act1.done = True
        self.assertEquals(self.act1.state, 'done')

    def test_activity_user_count(self):
        self.employee.activity_user_count()
