# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import common


class TestMailActivityReminder(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env(context=dict(
            cls.env.context,
            tracking_disable=True,
            no_reset_password=True,
        ))
        cls.ResUsers = cls.env['res.users']
        cls.Company = cls.env['res.company']
        cls.MailActivityType = cls.env['mail.activity.type']
        cls.MailActivity = cls.env['mail.activity']
        cls.company_id = cls.Company._company_default_get()
        cls.now = datetime(2020, 4, 19, 15, 00)
        cls.today = cls.now.date()
        cls.model_res_partner = cls.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        cls.partner_DecoAddict = cls.env['res.partner'].search(
            [('name', 'ilike', 'Deco Addict')], limit=1
        )

    def test_none_reminders(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
        })
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_empty_reminders(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': ' -./',
        })
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_delimiters(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0 1_2/3.4t5',
        })
        self.assertEqual(activity_type._get_reminder_offsets(), [
            0, 1, 2, 3, 4, 5
        ])

    def test_first_notice_is_reminder(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0',
        })
        user = self.ResUsers.sudo().create({
            'name': 'User',
            'login': 'user',
            'email': 'user@example.com',
            'company_id': self.company_id.id,
        })
        activity = self.MailActivity.create({
            'summary': 'Activity',
            'activity_type_id': activity_type.id,
            'res_model_id': self.model_res_partner.id,
            'res_id': self.partner_DecoAddict.id,
            'date_deadline': self.today,
            'user_id': user.id,
        })

        self.assertTrue(activity.last_reminder_local)

    def test_reminder_behaviour(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0/2',
        })

        with freeze_time(self.now):
            activity = self.MailActivity.create({
                'summary': 'Activity',
                'activity_type_id': activity_type.id,
                'res_model_id': self.model_res_partner.id,
                'res_id': self.partner_DecoAddict.id,
                'date_deadline': self.today + relativedelta(days=5),
            })

        with freeze_time(self.now):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=3)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertEqual(activities, activity)
            activities.action_remind()

        with freeze_time(self.now + relativedelta(days=4)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertEqual(activities, activity)
            activities.action_remind()

        activity.active = False
        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

    def test_reminder_flow(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0/2',
        })

        with freeze_time(self.now):
            activity = self.MailActivity.create({
                'summary': 'Activity',
                'activity_type_id': activity_type.id,
                'res_model_id': self.model_res_partner.id,
                'res_id': self.partner_DecoAddict.id,
                'date_deadline': self.today + relativedelta(days=5),
            })

        with freeze_time(self.now):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=3)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

        with freeze_time(self.now + relativedelta(days=4)):
            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

    def test_repeated_reminder(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0',
        })

        with freeze_time(self.now):
            activity = self.MailActivity.create({
                'summary': 'Activity',
                'activity_type_id': activity_type.id,
                'res_model_id': self.model_res_partner.id,
                'res_id': self.partner_DecoAddict.id,
                'date_deadline': self.today + relativedelta(days=1),
            })

        with freeze_time(self.now + relativedelta(days=1)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

    def test_overdue_reminder(self):
        activity_type = self.MailActivityType.create({
            'name': 'Activity Type',
            'reminders': '0',
        })

        with freeze_time(self.now):
            self.MailActivity.create({
                'summary': 'Activity',
                'activity_type_id': activity_type.id,
                'res_model_id': self.model_res_partner.id,
                'res_id': self.partner_DecoAddict.id,
                'date_deadline': self.today + relativedelta(days=1),
            })

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)
