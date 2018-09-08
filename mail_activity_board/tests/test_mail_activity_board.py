# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from .common import TestMailAcivityBoardCases
from odoo import fields
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class TestMailActivityBoardMethods(TestMailAcivityBoardCases):

    def setUp(self):
        super(TestMailActivityBoardMethods, self).setUp()
        # Set up activities

        lead_model_id = self.env['ir.model']._get('crm.lead').id
        partner_model_id = self.env['ir.model']._get('res.partner').id

        ActivityType = self.env['mail.activity.type']
        self.activity3 = ActivityType.create({
            'name': 'Celebrate the sale',
            'days': 3,
            'summary': 'ACT 3 : Beers for everyone because I am a good salesman !',
            'res_model_id': lead_model_id,
        })

        self.activity2 = ActivityType.create({
            'name': 'Call for Demo',
            'days': 6,
            'summary': 'ACT 2 : I want to show you my ERP !',
            'res_model_id': lead_model_id,
        })
        self.activity1 = ActivityType.create({
            'name': 'Initial Contact',
            'days': 5,
            'summary': 'ACT 1 : Presentation, barbecue, ... ',
            'res_model_id': lead_model_id,
        })

        # I create an opportunity, as salesman
        self.partner_client = self.env.ref("base.res_partner_1")
        self.lead = self.env['crm.lead'].sudo(self.crm_salesman.id).create({
            'name': 'Test Lead',
            'type': 'lead',
            'partner_id': self.partner_client.id,
            'team_id': self.env.ref("sales_team.team_sales_department").id,
            'user_id': self.crm_salesman.id,
        })
        self.oppor = self.env['crm.lead'].sudo(self.crm_salesman.id).create({
            'name': 'Test Opp',
            'type': 'opportunity',
            'partner_id': self.partner_client.id,
            'team_id': self.env.ref("sales_team.team_sales_department").id,
            'user_id': self.crm_salesman.id,
        })

        self.act_lead = self.env['mail.activity'].sudo(self.crm_salesman.id)\
            .create({
            'activity_type_id': self.activity1.id,
            'note': 'Lead activity.',
            'res_id': self.lead.id,
            'res_model_id': lead_model_id,
            })

        self.act_oppor1 = self.env['mail.activity'].sudo(self.crm_salesman.id)\
            .create({
            'activity_type_id': self.activity1.id,
            'note': 'Opportunity activity 1.',
            'res_id': self.oppor.id,
            'res_model_id': lead_model_id,
            })

        self.act_oppor2 = self.env['mail.activity'].sudo(self.crm_salesman.id)\
            .create({
            'activity_type_id': self.activity2.id,
            'note': 'Opportunity activity 2.',
            'res_id': self.oppor.id,
            'res_model_id': lead_model_id,
            })

        self.act_oppor3 = self.env['mail.activity'].sudo(self.crm_salesman.id)\
            .create({
            'activity_type_id': self.activity3.id,
            'note': 'Opportunity activity 3.',
            'res_id': self.oppor.id,
            'res_model_id': lead_model_id,
            })

        self.act_partner = self.env['mail.activity']\
            .sudo(self.crm_salesman.id).create({
            'activity_type_id': self.activity1.id,
            'note': 'Partner activity.',
            'res_id': self.partner_client.id,
            'res_model_id': partner_model_id,
            })


    def get_view(self, activity):
        action = activity.open_origin()
        result = self.env[action.get('res_model')] \
            .load_views(action.get('views'))
        return result.get('fields_views').get(action.get('view_mode'))

    def test_open_origin_crm_lead(self):
        """ This test case checks
                -If the method redirects to the form view of the correct one
                of an object of the 'crm.lead' class to which the activity
                belongs, depending on whether it is of the 'lead' or
                'opportunity' type.
        """
        # Id of the form view for the class 'crm.lead', type 'lead'
        form_view_lead_id = self.env.ref('crm.crm_case_form_view_leads').id

        # Id of the form view return open_origin()
        view = self.get_view(self.act_lead)
        # Check the next view is correct
        self.assertEqual(form_view_lead_id, view.get('view_id'))

        # Id of the form view for the class 'crm.lead', type 'opportunity'
        form_view_oppor_id = self.oppor.get_formview_id()

        # Id of the form view return open_origin()
        view = self.get_view(self.act_oppor1)

        # Check the next view is correct
        self.assertEqual(form_view_oppor_id, view.get('view_id'))

    def test_open_origin_res_partner(self):
        """ This test case checks
                - If the method redirects to the form view of the correct one
                of an object of the 'res.partner' class to which the activity
                belongs.
        """
        # Id of the form view for the class 'crm.lead', type 'lead'
        form_view_partner_id = self.env.ref('base.view_partner_form').id

        # Id of the form view return open_origin()
        view = self.get_view(self.act_partner)

        # Check the next view is correct
        self.assertEqual(form_view_partner_id, view.get('view_id'))

    def test_redirect_to_activities(self):
        """ This test case checks
                - if the method returns the correct action,
                - if the correct activities are shown.
        """
        action_id = self.env.ref(
            'mail_activity_board.open_boards_activities').read()[0].id
        action = self.oppor.redirect_to_activities(**{'id':self.oppor.id})
        self.assertEqual(action.id, action_id)

        kwargs = {
            'groupby': [
                "activity_type_id"
            ]
        }
        kwargs['domain'] = action.get('domain')

        result = self.env[action.get('res_model')] \
            .load_views(action.get('views'))

        fields = result.get('fields_views').get('kanban').get('fields')
        kwargs['fields'] = list(fields.keys())

        result = self.env['mail.activity'].read_group(**kwargs)

        acts = []
        for group in result:
            records = self.env['mail.activity'].search_read(
                domain= group.get('__domain'), fields=kwargs['fields']
            )
            acts += [id.get('id') for id in records]

        for act in acts:
            self.assertIn(act, self.oppor.activity_ids.ids)
