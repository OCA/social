# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo.tests import common, new_test_user


class TestMailNoUserAssignNotification(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="test_user")
        cls.icp = cls.env.ref(
            "mail_no_user_assign_notification.no_user_assign_notification_models"
        )
        cls.icp.value = "res.partner"
        # patch registry to simulate a ready environment
        # so that _message_auto_subscribe_notify
        # will be executed with the associated notification
        cls.env.registry.ready = True

    def _get_mail_messages(self, record):
        return self.env["mail.message"].search(
            [("model", "=", record._name), ("res_id", "=", record.id)]
        )

    def test_partner_create(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test partner",
                "user_id": self.user.id,
            }
        )
        all_messages = self._get_mail_messages(partner)
        # Message with user_notification is created when the assignment email is sent.
        self.assertNotIn("user_notification", all_messages.mapped("message_type"))
        # Remove model from config parameter (default behavior)
        self.icp.value = ""
        extra_partner = self.env["res.partner"].create(
            {
                "name": "Test partner extra",
                "user_id": self.user.id,
            }
        )
        all_messages = self._get_mail_messages(extra_partner)
        message = all_messages.filtered(lambda x: x.message_type == "user_notification")
        self.assertIn("You have been assigned to", message.body)

    def test_partner_write(self):
        partner = self.env["res.partner"].create({"name": "Test partner"})
        all_messages = self._get_mail_messages(partner)
        partner.write({"user_id": self.user.id})
        new_messages = self._get_mail_messages(partner) - all_messages
        # Message with user_notification is created when the assignment email is sent.
        self.assertNotIn("user_notification", new_messages.mapped("message_type"))
        # Remove model from config parameter (default behavior)
        self.icp.value = ""
        extra_partner = self.env["res.partner"].create({"name": "Test partner extra"})
        all_messages = self._get_mail_messages(extra_partner)
        extra_partner.write({"user_id": self.user.id})
        new_messages = self._get_mail_messages(extra_partner) - all_messages
        self.assertIn("You have been assigned to", new_messages.body)
