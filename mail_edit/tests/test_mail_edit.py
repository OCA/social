# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestMailMessage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Mail Edit Destination Partner",
            }
        )
        cls.message = cls.env["mail.message"].create(
            {
                "body": "<p>Message body</p>",
                "model": "res.partner",
                "res_id": cls.partner.id,
                "message_type": "comment",
                "author_id": cls.env.user.partner_id.id,
                "record_name": cls.partner.display_name,
            }
        )

    def test_get_model_selection_contains_partner(self):
        selection = dict(self.env["mail.message"]._get_model_selection())
        self.assertIn("res.partner", selection)

    def test_change_destination_object_sets_message_values(self):
        message = self.env["mail.message"].create(
            {
                "body": "<p>Message to move</p>",
                "message_type": "comment",
            }
        )

        message.destination_object_id = self.partner
        message.change_destination_object()

        self.assertEqual(message.model, "res.partner")
        self.assertEqual(message.res_id, self.partner.id)
        self.assertIn(self.partner.display_name, message.record_name)

    def test_change_destination_object_clears_message_values(self):
        self.message.destination_object_id = False
        self.message.change_destination_object()

        self.assertFalse(self.message.model)
        self.assertFalse(self.message.res_id)
        self.assertFalse(self.message.record_name)

    def test_message_read_dict_postprocess_adds_author_flag(self):
        message_dict = {
            "author_id": [self.env.user.partner_id.id, self.env.user.name],
        }
        messages = [message_dict]

        result = self.env["mail.message"]._message_read_dict_postprocess(
            messages,
            {},
        )

        self.assertEqual(result, messages)
        self.assertTrue(message_dict["is_author"])

    def test_message_read_dict_postprocess_adds_superuser_flag(self):
        group = self.env.ref("mail_edit.group_mail_edit_superuser")
        self.env.user.write({"groups_id": [(4, group.id)]})

        message_dict = {
            "author_id": [self.env.user.partner_id.id, self.env.user.name],
        }
        messages = [message_dict]

        self.env["mail.message"]._message_read_dict_postprocess(
            messages,
            {},
        )

        self.assertTrue(message_dict["is_superuser"])
        self.assertTrue(message_dict["is_author"])
