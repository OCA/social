# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from psycopg2 import IntegrityError

from odoo.tests.common import SavepointCase
from odoo.tools import mute_logger


class TestContactUnique(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.mailing_contact = cls.env["mailing.contact"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
            }
        )

    def test_contact_unique(self):
        with mute_logger("odoo.sql_db"):
            with self.assertRaisesRegex(IntegrityError, "mailing_contact_unique_email"):
                self.env["mailing.contact"].create(
                    {
                        "name": "John Doe 2",
                        "email": "john.doe@example.com",
                    }
                )
                self.env["mailing.contact"].flush()
