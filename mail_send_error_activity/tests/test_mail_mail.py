from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailMail(TransactionCase):
    def setUp(self):
        super(TestMailMail, self).setUp()
        self.env = self.env(
            context=dict(
                self.env.context,
                tracking_disable=True,
                no_reset_password=True,
            )
        )
        MailMail = self.env["mail.mail"]
        ResPartner = self.env["res.partner"]
        ResUsers = self.env["res.users"]

        self.res_users_test = ResUsers.create(
            {
                "name": "Test",
                "login": "test",
                "email": "test@example.com",
            }
        )

        self.res_partner_target = ResPartner.create(
            {
                "name": "Target",
            }
        )

        self.res_partner_bob = ResPartner.create(
            {
                "name": "Bob",
                "email": "bob@example.com",
            }
        )

        self.mail_mail_record_1 = MailMail.create(
            {
                "author_id": self.res_users_test.partner_id.id,
                "subject": "Test Mail Message #1",
                "email_from": '"Mitchell Admin" <admin@yourcompany.example.com>',
                "partner_ids": [(4, self.res_partner_bob.id)],
                "body_html": "Test Mail Message Body",
                "res_id": 0,
                "model": False,
            }
        )

        self.mail_mail_record_2 = MailMail.create(
            {
                "author_id": self.res_users_test.partner_id.id,
                "subject": "Test Mail Message #1",
                "email_from": '"Mitchell Admin" <admin@yourcompany.example.com>',
                "partner_ids": [(4, self.res_partner_bob.id)],
                "body_html": "Test Mail Message Body",
                "res_id": self.mail_mail_record_1.id,
                "model": self.mail_mail_record_1._name,
            }
        )

        self.mail_mail_record_3 = MailMail.sudo().create(
            {
                "author_id": self.res_users_test.partner_id.id,
                "subject": "Test Mail Message #3",
                "email_from": '"Mitchell Admin" <admin@yourcompany.example.com>',
                "partner_ids": [(4, self.res_partner_bob.id)],
                "body_html": "Test Mail Message Body",
                "res_id": self.res_partner_target.id,
                "model": self.res_partner_bob._name,
            }
        )

        self.env["mail.mail"]._patch_method("unlink", lambda *args: True)

    def get_mail_activity_record(self):
        res_id = self.res_partner_target.id
        model_id = self.env["ir.model"]._get(self.res_partner_target._name).id
        return self.env["mail.activity"].search(
            [
                ("res_id", "=", res_id),
                ("res_model_id", "=", model_id),
            ]
        )

    def test_no_activity_vals(self):
        """Ensure that returned empty values"""
        result = self.mail_mail_record_1._prepare_mail_error_activity_vals()
        self.assertFalse(result, msg="Vals must be empty dict")
        result = self.mail_mail_record_2._prepare_mail_error_activity_vals()
        self.assertFalse(result, msg="Vals must be empty dict")
        self.mail_mail_record_1.write({"author_id": self.res_partner_bob.id})
        result = self.mail_mail_record_1._prepare_mail_error_activity_vals()
        self.assertFalse(result, msg="Vals must be empty dict")
        self.mail_mail_record_1.write({"author_id": self.res_partner_bob.id})
        result = self.mail_mail_record_2._prepare_mail_error_activity_vals()
        self.assertFalse(result, msg="Vals must be empty dict")

    def test_activity_vals(self):
        """Ensure that activity values correct"""
        result = self.mail_mail_record_3._prepare_mail_error_activity_vals()
        activity_type_id = self.ref(
            "mail_send_error_activity.mail_activity_data_mail_send_error"
        )
        self.assertEqual(
            activity_type_id,
            result.get("activity_type_id"),
            msg="Activity id must be equal {}".format(activity_type_id),
        )
        summary = "Error while sending mail bob@example.com"
        self.assertEqual(
            result.get("summary"),
            summary,
            msg="Summary must be equal {}".format(summary),
        )
        model_id = self.env["ir.model"]._get(self.res_partner_bob._name).id
        self.assertEqual(
            result.get("res_model_id"),
            model_id,
            msg="Model id must be equal {}".format(model_id),
        )
        res_id = self.res_partner_target.id
        self.assertEqual(
            result.get("res_id"), res_id, msg="Res id must be equal {}".format(res_id)
        )

    def test_no_mail_send_error(self):
        """Ensure that no activity is created when there is no mail send error"""
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_send_error_activity.activity_on_mail_error", False
        )
        self.mail_mail_record_3._postprocess_sent_message(
            success_pids=[], failure_type=False, failure_reason=False
        )
        empty_activity_records = self.get_mail_activity_record()
        self.assertEqual(
            len(empty_activity_records), 0, msg="Records count must be equal 0"
        )
        self.mail_mail_record_3._postprocess_sent_message(
            success_pids=[], failure_type="SMTP", failure_reason=False
        )
        empty_activity_records = self.get_mail_activity_record()
        self.assertEqual(
            len(empty_activity_records), 0, msg="Records count must be equal 0"
        )
        self.mail_mail_record_3.write({"author_id": self.env["res.partner"]})
        self.mail_mail_record_3._postprocess_sent_message(
            success_pids=[], failure_type="SMTP", failure_reason=False
        )
        empty_activity_records = self.get_mail_activity_record()
        self.assertEqual(
            len(empty_activity_records), 0, msg="Records count must be equal 0"
        )

    def test_mail_send_error(self):
        """Ensure that activity is created when there is a mail send error"""
        self.mail_mail_record_3.write({"state": "exception"})
        activity = self.get_mail_activity_record()
        self.assertFalse(activity, msg="Activity must be False")
        self.env["ir.config_parameter"].sudo().set_param(
            "mail_send_error_activity.activity_on_mail_error", True
        )
        self.mail_mail_record_3.write({"state": "exception"})
        self.mail_mail_record_3._postprocess_sent_message(
            success_pids=[], failure_type="SMTP", failure_reason=False
        )
        activity_record = self.get_mail_activity_record()
        self.assertEqual(
            len(activity_record), 1, msg="Records count must be equal to 1"
        )
        activity_type_id = self.ref(
            "mail_send_error_activity.mail_activity_data_mail_send_error"
        )
        model_id = self.env["ir.model"]._get(self.res_partner_target._name).id
        self.assertEqual(
            activity_record.activity_type_id.id,
            activity_type_id,
            msg="Activity type must be equal {}".format(activity_type_id),
        )
        self.assertEqual(
            activity_record.res_model_id.id,
            model_id,
            msg="Activity model id must be equal {}".format(model_id),
        )
        self.assertEqual(
            activity_record.res_id,
            self.res_partner_target.id,
            msg="Activity res_id must be equal {}".format(self.res_partner_target.id),
        )
