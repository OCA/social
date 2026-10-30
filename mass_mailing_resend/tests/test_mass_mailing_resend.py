# Copyright 2017-2020 Tecnativa - Pedro M. Baeza
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import exceptions
from odoo.tests import common


class TestMassMailingResend(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.list = cls.env["mailing.list"].create({"name": "Test list"})
        cls.contact1 = cls.env["mailing.contact"].create(
            {
                "name": "Contact 1",
                "email": "email1@test.com",
                "list_ids": [[6, 0, [cls.list.id]]],
            }
        )
        cls.contact2 = cls.env["mailing.contact"].create(
            {
                "name": "Contact 2",
                "email": "email2@test.com",
                "list_ids": [[6, 0, [cls.list.id]]],
            }
        )
        cls.mass_mailing = cls.env["mailing.mailing"].create(
            {
                "name": "Test mass mailing",
                "email_from": "test@example.org",
                "mailing_model_id": cls.env.ref("mass_mailing.model_mailing_list").id,
                "contact_list_ids": [(6, 0, cls.list.ids)],
                "subject": "Mailing test",
            }
        )
        cls.mm_cron = cls.env.ref("mass_mailing.ir_cron_mass_mailing_queue").sudo()

    def test_resend_error(self):
        with self.assertRaises(exceptions.UserError):
            self.mass_mailing.button_draft()

    def _mailing_action_done(self):
        self.mass_mailing.action_launch()
        self.mm_cron.method_direct_trigger()

    def test_resend_process(self):
        # Send mailing
        self._mailing_action_done()
        self.assertEqual(self.mass_mailing.state, "done")
        self.assertEqual(len(self.mass_mailing.mailing_trace_ids), 2)
        # Simulate that an email has not been sent
        self.mass_mailing.mailing_trace_ids.filtered(
            lambda x: x.email == self.contact2.email
        ).unlink()
        self.assertEqual(len(self.mass_mailing.mailing_trace_ids), 1)
        # Back to draft
        self.mass_mailing.button_draft()
        self.assertEqual(self.mass_mailing.state, "draft")
        # Send mailing again (already sent not sent again)
        self._mailing_action_done()
        self.assertEqual(self.mass_mailing.state, "done")
        self.assertEqual(len(self.mass_mailing.mailing_trace_ids), 2)
