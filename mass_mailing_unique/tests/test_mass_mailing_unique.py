# Copyright 2016 Tecnativa - Pedro M. Baeza
# Copyright 2021 Camptocamp - Iván Todorovich
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import common
from odoo.tools import mute_logger

from ..hooks import pre_init_hook


class TestMassMailingUnique(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_data")
        cls.mailing_contact = cls.env["mailing.contact"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "list_ids": [(6, 0, cls.mailing_list.ids)],
            }
        )

    def test_init_hook_list_mailing_list(self):
        # Disable temporarily the constraint
        self.env.cr.execute(
            """
                ALTER TABLE mailing_list
                DROP CONSTRAINT mailing_list_unique_name
            """
        )
        # Create another list with the same exact name
        self.env["mailing.list"].create({"name": self.mailing_list.name})
        with self.assertRaises(ValidationError):
            pre_init_hook(self.env.cr)

    def test_init_hook_list_mailing_contact(self):
        # Disable temporarily the constraint
        self.env.cr.execute(
            """
                ALTER TABLE mailing_contact
                DROP CONSTRAINT mailing_contact_unique_email
            """
        )
        # Create another list with the same exact name
        self.env["mailing.contact"].create(
            {
                "name": f"{self.mailing_contact.name} (2)",
                "email": self.mailing_contact.email,
            }
        )
        self.env["mailing.contact"].flush_model()
        with self.assertRaises(ValidationError):
            pre_init_hook(self.env.cr)

    def test_mailing_contact_unique_email_exact(self):
        """Create a contact with the same exact email"""
        with mute_logger("odoo.sql_db"):
            with self.assertRaisesRegex(IntegrityError, "mailing_contact_unique_email"):
                self.env["mailing.contact"].create(
                    {
                        "name": "John Doe (2)",
                        "email": "john.doe@example.com",
                    }
                )
                self.env["mailing.contact"].flush_model()

    def test_mailing_contact_unique_email_same(self):
        """Create a contact with the same email (not exact though)"""
        with mute_logger("odoo.sql_db"):
            with self.assertRaisesRegex(IntegrityError, "mailing_contact_unique_email"):
                self.env["mailing.contact"].create(
                    {
                        "name": "John Doe (2)",
                        "email": "<John Doe> John.DOE@example.com",
                    }
                )
                self.env["mailing.contact"].flush_model()

    def test_mailing_contact_unique_email_ok(self):
        """Create a contact with another email"""
        self.env["mailing.contact"].create(
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
            }
        )

    def test_mailing_list_unique_name_duplicated(self):
        """Create a mailing list with the same name"""
        with mute_logger("odoo.sql_db"):
            with self.assertRaisesRegex(IntegrityError, "mailing_list_unique_name"):
                self.env["mailing.list"].create(
                    {
                        "name": self.mailing_list.name,
                    }
                )
                self.env["mailing.list"].flush_model()

    def test_mailing_list_unique_name_ok(self):
        """Create a mailing list with another name"""
        self.env["mailing.list"].create(
            {
                "name": "Another mailing list",
            }
        )
