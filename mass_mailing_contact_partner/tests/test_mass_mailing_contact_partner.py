# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestContactPartner(SavepointCase):
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
        cls.partner_john = cls.env["res.partner"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
            }
        )
        cls.partner_jane = cls.env["res.partner"].create(
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
            }
        )

    def test_contact_partner(self):
        self.assertEqual(self.mailing_contact.partner_count, 1)
        self.assertEqual(self.mailing_contact.partner_ids, self.partner_john)
        # Create a jane.doe contact
        contact = self.env["mailing.contact"].create(
            {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
            }
        )
        self.assertEqual(contact.partner_count, 1)
        self.assertEqual(contact.partner_ids, self.partner_jane)
        # Change jane's address to be the same than john
        self.partner_jane.email = "John.DOE@example.com"
        self.assertEqual(self.mailing_contact.partner_count, 2)
        self.assertEqual(
            self.mailing_contact.partner_ids,
            self.partner_john | self.partner_jane,
        )
        # Change mailing.contact address
        self.mailing_contact.email = "unknown@example.com"
        self.assertEqual(self.mailing_contact.partner_count, 0)

    def test_contact_partner_action(self):
        action = self.mailing_contact.action_view_partner_ids()
        partners = self.env["res.partner"].search(action["domain"])
        self.assertEqual(partners, self.partner_john)
