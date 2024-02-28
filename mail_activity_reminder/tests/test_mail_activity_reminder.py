# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import common


class TestMailActivityReminder(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env = cls.env(
            context=dict(
                cls.env.context,
                tracking_disable=True,
                no_reset_password=True,
            )
        )
        cls.ResUsers = cls.env["res.users"]
        cls.Company = cls.env["res.company"]
        cls.MailActivityType = cls.env["mail.activity.type"]
        cls.MailActivity = cls.env["mail.activity"]
        cls.company_id = cls.Company._company_default_get()
        cls.now = datetime(2020, 4, 19, 15, 00)
        cls.today = cls.now.date()
        cls.model_res_partner = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        cls.partner_DecoAddict = cls.env["res.partner"].search(
            [("name", "ilike", "Deco Addict")], limit=1
        )
        cls.partner_Azure = cls.env["res.partner"].search(
            [("name", "ilike", "Azure Interior")], limit=1
        )
        cls.partner_Gemini = cls.env["res.partner"].search(
            [("name", "ilike", "Gemini Furniture")], limit=1
        )

    def test_none_reminders(self):
        activity_type = self.MailActivityType.create({"name": "Activity Type"})
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_empty_reminders(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": " -./"}
        )
        self.assertEqual(activity_type._get_reminder_offsets(), [])

    def test_delimiters(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0 1_2/3.4t5"}
        )
        self.assertEqual(activity_type._get_reminder_offsets(), [0, 1, 2, 3, 4, 5])

    def test_first_notice_is_reminder(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )
        user = self.ResUsers.sudo().create(
            {
                "name": "User",
                "login": "user",
                "email": "user@example.com",
                "company_id": self.company_id.id,
            }
        )
        activity = self.MailActivity.create(
            {
                "summary": "Activity",
                "activity_type_id": activity_type.id,
                "res_model_id": self.model_res_partner.id,
                "res_id": self.partner_DecoAddict.id,
                "date_deadline": self.today,
                "user_id": user.id,
            }
        )

        self.assertTrue(activity.last_reminder_local)

    def test_reminder_behaviour(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner_DecoAddict.id,
                    "date_deadline": self.today + relativedelta(days=5),
                }
            )

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

        activity.unlink()
        with freeze_time(self.now + relativedelta(days=5)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

    def test_reminder_flow(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0/2"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner_DecoAddict.id,
                    "date_deadline": self.today + relativedelta(days=5),
                }
            )

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
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )

        with freeze_time(self.now):
            activity = self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner_DecoAddict.id,
                    "date_deadline": self.today + relativedelta(days=1),
                }
            )

        with freeze_time(self.now + relativedelta(days=1)):
            activities = self.MailActivity._process_reminders()
            self.assertEqual(activities, activity)

            activities = self.MailActivity._process_reminders()
            self.assertFalse(activities)

    def test_overdue_reminder(self):
        activity_type = self.MailActivityType.create(
            {"name": "Activity Type", "reminders": "0"}
        )

        with freeze_time(self.now):
            self.MailActivity.create(
                {
                    "summary": "Activity",
                    "activity_type_id": activity_type.id,
                    "res_model_id": self.model_res_partner.id,
                    "res_id": self.partner_DecoAddict.id,
                    "date_deadline": self.today + relativedelta(days=1),
                }
            )

        with freeze_time(self.now + relativedelta(days=2)):
            activities = self.MailActivity._get_activities_to_remind()
            self.assertFalse(activities)

    def test_mail_reminder_per_type(self):
        mt = self.env.ref("mail_activity_reminder.message_activity_assigned")
        mt_copy1 = mt.copy()
        mt_copy2 = mt.copy()
        activity_type1 = self.MailActivityType.create(
            {
                "name": "Activity Type 1",
                "reminders": "0",
            }
        )
        activity_type2 = self.MailActivityType.create(
            {
                "name": "Activity Type 2",
                "reminders": "0",
                "reminder_mail_template_id": mt_copy1.id,
            }
        )
        activity_type3 = self.MailActivityType.create(
            {
                "name": "Activity Type 3",
                "reminders": "0",
                "reminder_mail_template_id": mt_copy2.id,
            }
        )
        user = self.ResUsers.sudo().create(
            {
                "name": "User",
                "login": "user",
                "email": "user@example.com",
                "company_id": self.company_id.id,
            }
        )
        with freeze_time(self.now):
            activities = self.MailActivity.create(
                [
                    # Activity using generic mail template
                    {
                        "summary": "Activity 1",
                        "activity_type_id": activity_type1.id,
                        "res_model_id": self.model_res_partner.id,
                        "res_id": self.partner_DecoAddict.id,
                        "date_deadline": self.today + relativedelta(days=1),
                        "user_id": user.id,
                    },
                    # Activities using dedicated mail templates
                    {
                        "summary": "Activity 2",
                        "activity_type_id": activity_type2.id,
                        "res_model_id": self.model_res_partner.id,
                        "res_id": self.partner_Azure.id,
                        "date_deadline": self.today + relativedelta(days=1),
                        "user_id": user.id,
                    },
                    {
                        "summary": "Activity 3",
                        "activity_type_id": activity_type3.id,
                        "res_model_id": self.model_res_partner.id,
                        "res_id": self.partner_Gemini.id,
                        "date_deadline": self.today + relativedelta(days=1),
                        "user_id": user.id,
                    },
                ]
            )
        with freeze_time(self.now + relativedelta(days=1)):
            with common.RecordCapturer(self.env["mail.message"], []) as capt:
                activities = self.MailActivity._process_reminders()
            self.assertTrue(all(a.last_reminder_local for a in activities))
            # 3 messages posted (1 per mail template)
            self.assertEqual(len(capt.records), 3)
