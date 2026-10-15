# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date, datetime
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import common, new_test_user


class TestLastMessageDate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner_model = cls.env["res.partner"]
        # One create() so that a read computes the field for all three at once.
        cls.partners = cls.partner_model.create(
            [{"name": "Partner 1"}, {"name": "Partner 2"}, {"name": "Partner 3"}]
        )
        cls.partner_1, cls.partner_2, cls.partner_3 = cls.partners

    def _create_message(self, record, date, message_type="comment"):
        return self.env["mail.message"].create(
            {
                "message_type": message_type,
                "model": record._name,
                "res_id": record.id,
                "body": "Test message",
                "date": date,
            }
        )

    def test_latest_message(self):
        # An email fetched later can carry an older Date header.
        self._create_message(self.partner_1, datetime(2026, 1, 2), "email")
        self._create_message(self.partner_1, datetime(2026, 1, 1), "email")
        self._create_message(self.partner_2, datetime(2026, 1, 5))
        # System and user notifications don't count by default.
        self._create_message(self.partner_1, datetime(2026, 1, 3), "notification")
        self.partner_1.message_notify(
            partner_ids=self.partner_2.ids, body="Test notification"
        )
        self.assertEqual(
            self.partners.mapped("last_message_date"),
            [datetime(2026, 1, 2), datetime(2026, 1, 5), False],
        )

    def test_no_message_types(self):
        self._create_message(self.partner_1, datetime(2026, 1, 1))
        with patch.object(
            type(self.partner_model), "_get_tracked_message_types", return_value=[]
        ):
            self.assertFalse(self.partner_1.last_message_date)
            self.assertFalse(
                self.partner_model.search(
                    [
                        ("id", "in", self.partners.ids),
                        ("last_message_date", "!=", False),
                    ]
                )
            )

    def test_message_types_parameter(self):
        self._create_message(self.partner_1, datetime(2026, 1, 2), "email")
        self._create_message(self.partner_1, datetime(2026, 1, 3), "comment")
        self._create_message(self.partner_1, datetime(2026, 1, 4), "notification")
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("mail_last_message_date.message_types", "email")
        self.assertEqual(self.partner_1.last_message_date, datetime(2026, 1, 2))
        self.assertFalse(
            self.partner_model.search(
                [
                    ("id", "=", self.partner_1.id),
                    ("last_message_date", ">", datetime(2026, 1, 2)),
                ]
            )
        )
        params.set_param("mail_last_message_date.message_types", "email, notification")
        self.partner_1.invalidate_cache(["last_message_date"])
        self.assertEqual(self.partner_1.last_message_date, datetime(2026, 1, 4))
        # Without a valid type, or without the parameter, no message counts.
        params.set_param("mail_last_message_date.message_types", "unknown")
        self.partner_1.invalidate_cache(["last_message_date"])
        self.assertFalse(self.partner_1.last_message_date)
        params.set_param("mail_last_message_date.message_types", False)
        self.partner_1.invalidate_cache(["last_message_date"])
        self.assertFalse(self.partner_1.last_message_date)

    def test_search(self):
        self._create_message(self.partner_1, datetime(2026, 1, 1, 10, 0))
        self._create_message(self.partner_2, datetime(2026, 1, 3))
        partners = self.partner_1 | self.partner_2 | self.partner_3

        def search(operator, value):
            return self.partner_model.search(
                [("id", "in", partners.ids), ("last_message_date", operator, value)]
            )

        self.assertEqual(search("<", datetime(2026, 1, 2)), self.partner_1)
        self.assertEqual(search("<", "2026-01-02"), self.partner_1)
        # A date-only value covers the whole day, as on a stored datetime.
        self.assertEqual(search("<=", "2026-01-01"), self.partner_1)
        self.assertEqual(search(">", "2026-01-01"), self.partner_2)
        self.assertEqual(search(">", date(2026, 1, 1)), self.partner_2)
        self.assertEqual(search(">=", datetime(2026, 1, 3)), self.partner_2)
        self.assertEqual(search("=", datetime(2026, 1, 1, 10, 0)), self.partner_1)
        self.assertEqual(
            search("!=", datetime(2026, 1, 1, 10, 0)), self.partner_2 | self.partner_3
        )
        self.assertEqual(search("=", False), self.partner_3)
        self.assertEqual(search("!=", False), self.partner_1 | self.partner_2)

    def test_internal_users_only(self):
        self._create_message(self.partner_1, datetime(2026, 1, 1))
        internal_user = new_test_user(
            self.env, login="last_message_date_internal", groups="base.group_user"
        )
        portal_user = new_test_user(
            self.env, login="last_message_date_portal", groups="base.group_portal"
        )
        internal_partners = self.partner_model.with_user(internal_user)
        self.assertIn("last_message_date", internal_partners.fields_get())
        self.assertEqual(
            internal_partners.search(
                [("id", "in", self.partners.ids), ("last_message_date", "!=", False)]
            ),
            self.partner_1,
        )
        self.assertNotIn(
            "last_message_date",
            self.partner_model.with_user(portal_user).fields_get(),
        )
        with self.assertRaises(AccessError):
            self.partner_model.with_user(portal_user).search(
                [("last_message_date", "!=", False)]
            )
