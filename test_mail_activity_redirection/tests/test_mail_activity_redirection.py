from odoo.addons.test_mail.tests.test_mail_activity import TestActivityCommon
from odoo.tests.common import post_install, at_install


@at_install(False)
@post_install(True)
class TestMailActivityRedirection(TestActivityCommon):
    @classmethod
    def setUpClass(cls):
        super(TestMailActivityRedirection, cls).setUpClass()
        self = cls
        # Create an instance of a mail test activity model alternative
        self.test_record_alt = self.env['mail.test.activity.alt'].with_context(
            TestActivityCommon._test_context
        ).create({'name': 'Test Alt'})
        # Reset ctx
        self.test_record = self.test_record.with_context(
            mail_create_nolog=False,
            mail_create_nosubscribe=False,
            mail_notrack=False
        )
        # Delete all existing rules (created from data)
        redirection_ids = self.env['mail.activity.redirection'].search([])
        redirection_ids.unlink()

    def test_mail_activity_automation_skip(self):
        activity = self.test_record.with_context(
            mail_activity_automation_skip=True,
        ).activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(not activity)

    def test_redirect_all(self):
        redirection = self.env['mail.activity.redirection'].create(
            {
                'name': "Redirect all to Ernest",
                'sequence': 10,
                'user_id': self.user_employee.id,
            }
        )

        activity = self.test_record.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

    def test_redirect_using_model(self):
        model_mail_test_activity = self.env['ir.model'].sudo().search(
            [('model', '=', 'mail.test.activity')], limit=1
        )
        redirection = self.env['mail.activity.redirection'].create(
            {
                'name':
                    "Redirect only activities from `mail.test.activity` "
                    "to Ernest",
                'sequence': 10,
                'user_id': self.user_employee.id,
                'model_ids': [(6, 0, [model_mail_test_activity.id])],
            }
        )

        activity = self.test_record.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_admin)
        self.assertFalse(activity.id in redirection.activity_ids.ids)

    def test_redirect_using_activity_type(self):
        mail_act_test_todo = self.env.ref('test_mail.mail_act_test_todo')
        mail_act_test_meeting = self.env.ref('test_mail.mail_act_test_meeting')
        redirection = self.env['mail.activity.redirection'].create(
            {
                'name':
                    "Redirect only activities of type `mail.test.activity` "
                    "to Ernest",
                'sequence':
                    10,
                'user_id':
                    self.user_employee.id,
                'activity_type_ids':
                    [
                        (
                            6, 0, [
                                mail_act_test_todo.id,
                                mail_act_test_meeting.id,
                            ]
                        )
                    ],
            }
        )

        activity = self.test_record.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_meeting',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_call',
            user_id=self.user_admin.id,
        )
        self.assertTrue(activity.user_id == self.user_admin)
        self.assertFalse(activity.id in redirection.activity_ids.ids)

    def test_redirect_using_qweb(self):
        act_template_1 = self.env.ref(
            'test_mail_activity_redirection.act_template_1'
        )

        redirection = self.env['mail.activity.redirection'].create(
            {
                'name':
                    "Redirect only activities using `act_template_1` qweb "
                    "template to Ernest",
                'sequence': 10,
                'user_id': self.user_employee.id,
                'qweb_templates': [(6, 0, [
                    act_template_1.id,
                ])],
            }
        )

        activity = self.test_record.activity_schedule_with_view(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
            views_or_xmlid='test_mail_activity_redirection.act_template_1',
            render_context={}
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        activity = self.test_record.activity_schedule_with_view(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
            views_or_xmlid='test_mail_activity_redirection.act_template_2',
            render_context={}
        )
        self.assertTrue(activity.user_id == self.user_admin)
        self.assertFalse(activity.id in redirection.activity_ids.ids)

    def test_redirect_using_regex(self):
        redirection = self.env['mail.activity.redirection'].create(
            {
                'name':
                    "Redirect only activities that match a regular expression "
                    "to Ernest",
                'sequence': 10,
                'user_id': self.user_employee.id,
                'regex_pattern': r'Lorem',
            }
        )
        act_template_1 = self.env.ref(
            'test_mail_activity_redirection.act_template_1'
        )
        note = act_template_1.render(values={})

        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
            note=note,
        )
        self.assertTrue(activity.user_id == self.user_employee)
        self.assertTrue(activity.id in redirection.activity_ids.ids)

        act_template_2 = self.env.ref(
            'test_mail_activity_redirection.act_template_2'
        )
        note = act_template_2.render(values={})
        activity = self.test_record_alt.activity_schedule(
            'test_mail.mail_act_test_todo',
            user_id=self.user_admin.id,
            note=note,
        )
        self.assertTrue(activity.user_id == self.user_admin)
        self.assertFalse(activity.id in redirection.activity_ids.ids)
