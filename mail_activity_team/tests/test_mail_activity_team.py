# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo.fields import Datetime
from datetime import timedelta


class TestMailActivityTeam(TransactionCase):

    def setUp(self):
        super(TestMailActivityTeam, self).setUp()

        self.env["mail.activity.team"].search([]).unlink()

        self.employee = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Employee",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('base.group_partner_manager').id])]
        })

        self.employee2 = self.env['res.users'].create({
            'company_id': self.env.ref("base.main_company").id,
            'name': "Employee 2",
            'login': "csu2",
            'email': "crmuser2@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
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

        self.partner_client = self.env.ref("base.res_partner_1")

        self.act1 = self.env['mail.activity'].sudo(self.employee).create({
            'activity_type_id': self.activity1.id,
            'note': 'Partner activity 1.',
            'res_id': self.partner_client.id,
            'res_model_id': self.partner_ir_model.id,
            'user_id': self.employee.id,
        })

        self.team1 = self.env['mail.activity.team'].sudo().create({
            'name': 'Team 1',
            'res_model_ids': [(6, 0, [self.partner_ir_model.id])],
            'member_ids': [(6, 0, [self.employee.id])],
        })

        self.team2 = self.env['mail.activity.team'].sudo().create({
            'name': 'Team 2',
            'res_model_ids': [(6, 0, [self.partner_ir_model.id])],
            'member_ids': [(6, 0, [self.employee.id, self.employee2.id])],
        })

        self.act2 = self.env['mail.activity'].sudo(self.employee).create({
            'activity_type_id': self.activity2.id,
            'note': 'Partner activity 2.',
            'res_id': self.partner_client.id,
            'res_model_id': self.partner_ir_model.id,
            'user_id': self.employee.id,
        })

        self.act3 = self.env['mail.activity'].sudo(self.employee).create({
            'activity_type_id': self.browse_ref(
                'mail.mail_activity_data_meeting').id,
            'note': 'Meeting activity 3.',
            'res_id': self.partner_client.id,
            'res_model_id': self.partner_ir_model.id,
            'user_id': self.employee.id,
            'team_id': self.team1.id,
            'summary': 'Metting activity'
        })
        self.start = Datetime.now()
        self.stop = Datetime.to_string(
            Datetime.from_string(self.start) + timedelta(hours=1)
        )

    def test_meeting_blank(self):
        meeting = self.env['calendar.event'].sudo(self.employee).create({
            'start': self.start,
            'stop': self.stop,
            'name': 'Test meeting'
        })
        self.assertTrue(meeting.team_id)

    def test_meeting_from_activity(self):
        action = self.act3.with_context(
            default_res_id=self.act3.res_id,
            default_res_model=self.act3.res_model,
        ).action_create_calendar_event()

        meeting = self.env['calendar.event'].sudo(self.employee).with_context(
            **action['context']
        ).create({
            'start': self.start,
            'stop': self.stop
        })
        self.assertTrue(meeting.team_id)
        self.assertTrue(meeting.read(['description'])[0]['description'])
        self.assertTrue(
            meeting.sudo(self.employee2).read(
                ['description'])[0]['description'],
            'He should be able to read the record as it is public by default',
        )
        meeting.write({'privacy': 'team'})
        self.assertFalse(
            meeting.sudo(self.employee2).read(
                ['description'])[0]['description'],
            'He shouldn\'t be able to read the record as it is '
            'public by default',
        )

    def test_missing_activities(self):
        self.assertFalse(
            self.act1.team_id, 'Error: Activity 1 should not have a team.')
        self.assertEqual(self.team1.count_missing_activities, 1)
        self.team1.assign_team_to_unassigned_activities()
        self.team1._compute_missing_activities()
        self.assertEqual(self.team1.count_missing_activities, 0)
        self.assertEqual(self.act1.team_id, self.team1)

    def test_activity_onchanges(self):
        self.assertEqual(
            self.act2.team_id, self.team1,
            'Error: Activity 2 should have Team 1.')
        with self.env.do_in_onchange():
            self.act2.team_id = False
            self.act2._onchange_team_id()
            self.assertEqual(self.act2.user_id, self.employee)
            self.act2.team_id = self.team2
            self.act2._onchange_team_id()
            self.assertEqual(self.act2.user_id, self.employee)
            self.act2.user_id = self.employee2
            self.act2._onchange_user_id()
            self.assertEqual(self.act2.team_id, self.team2)
            self.act2.team_id = self.team1
            self.act2._onchange_team_id()
            self.assertEqual(self.act2.user_id, self.team1.member_ids)
            with self.assertRaises(ValidationError):
                self.act2.write({
                    'user_id': self.employee2.id,
                    'team_id': self.team1.id,
                })

    def test_team_onchanges(self):
        self.assertFalse(
            self.team2.user_id,
            'Error: Team 2 should not have a Team Leader yet.')
        with self.env.do_in_onchange():
            self.team2.user_id = self.employee
            self.team2.member_ids = [(3, self.employee.id)]
            self.team2._onchange_member_ids()
            self.assertFalse(self.team2.user_id)

    def test_activity_count(self):
        res = self.env['res.users'].with_context(
            {'team_activities': True}
        ).activity_user_count(
            user_id=self.employee.id
        )
        self.assertEqual(res[0]['total_count'], 0)
