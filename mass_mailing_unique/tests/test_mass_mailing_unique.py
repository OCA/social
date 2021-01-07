# Copyright 2016 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import exceptions
from odoo.tests import common, tagged

from ..hooks import pre_init_hook


@tagged("unique")
class TestMassMailingUnique(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestMassMailingUnique, cls).setUpClass()
        cls.list = cls.env["mailing.list"].create({"name": "Test list"})
        cls.contact1 = cls.env["mailing.contact"].create(
            {"name": "Contact 1", "email": "email1@test.com", "list_ids": [(6, 0, [cls.list.id])],}
        )

    def test_init_hook_list(self):
        # Disable temporarily the constraint
        self.env.cr.execute(
            """
            ALTER TABLE mailing_list
            DROP CONSTRAINT mailing_list_unique_name
            """
        )
        self.env["mailing.list"].create({"name": "Test list"})
        with self.assertRaises(exceptions.ValidationError):
            pre_init_hook(self.env.cr)

    def test_add_contact_with_list(self):
        with self.assertRaises(exceptions.ValidationError):
            self.env["mailing.contact"].create(
                {
                    "name": "Contact 2",
                    "email": "email1@test.com",
                    "list_ids": [(6, 0, [self.list.id])],
                }
            )

    def test_add_contact_with_subscription(self):
        with self.assertRaises(exceptions.ValidationError):
            self.env["mailing.contact"].create(
                {
                    "name": "Contact 2",
                    "email": "email1@test.com",
                    "subscription_list_ids": [(0, 0, {"list_id": self.list.id})],
                }
            )

    def test_add_list_with_contacts(self):
        contact2 = self.env["mailing.contact"].create(
            {"name": "Contact 2", "email": "email1@test.com"}
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["mailing.list"].create(
                {"name": "Test list 2", "contact_ids": [(6, 0, (self.contact1 | contact2).ids)],}
            )

    def test_add_list_with_subscriptions(self):
        contact2 = self.env["mailing.contact"].create(
            {"name": "Contact 2", "email": "email1@test.com"}
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["mailing.list"].create(
                {"name": "Test list 2", "contact_ids": [(6, 0, (self.contact1 | contact2).ids)],}
            )

    def test_add_list_contact_rel(self):
        contact2 = self.env["mailing.contact"].create(
            {"name": "Contact 2", "email": "email1@test.com"}
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["mailing.contact.subscription"].create(
                {"list_id": self.list.id, "contact_id": contact2.id}
            )
