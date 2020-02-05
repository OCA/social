# Copyright 2017-2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import exceptions
from odoo.tests import common


class TestMassMailingResend(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestMassMailingResend, cls).setUpClass()
        cls.list = cls.env["mailing.list"].create({"name": "Test list"})
        cls.contact1 = cls.env["mailing.contact"].create(
            {"name": "Contact 1", "email": "email1@test.com"}
        )
        cls.mass_mailing = cls.env["mailing.mailing"].create(
            {
                "name": "Test mass mailing",
                "email_from": "test@example.org",
                "mailing_model_id": cls.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(6, 0, cls.list.ids)],
                "subject": "Mailing test",
                "reply_to_mode": "thread",
            }
        )

    def test_resend_error(self):
        with self.assertRaises(exceptions.UserError):
            self.mass_mailing.button_draft()

    def test_resend(self):
        self.mass_mailing.state = "done"  # Force state
        self.assertEqual(self.mass_mailing.state, "done")
        self.mass_mailing.button_draft()
        self.assertEqual(self.mass_mailing.state, "draft")
