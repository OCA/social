# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestSubscriptionDate(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.mailing_list = cls.env.ref("mass_mailing.mailing_list_data")
        cls.mailing_contact = cls.env["mailing.contact"].create(
            {
                "name": "John Doe",
                "email": "john.doe@example.com",
            }
        )

    def test_subscription_date(self):
        # Create subscription
        subs = self.env["mailing.contact.subscription"].create(
            {
                "contact_id": self.mailing_contact.id,
                "list_id": self.mailing_list.id,
            }
        )
        self.assertTrue(subs.subscription_date)
        # Opt out
        subs.opt_out = True
        self.assertFalse(subs.subscription_date)

    def test_subscription_date_opt_out(self):
        # Create subscription already opted out
        subs = self.env["mailing.contact.subscription"].create(
            {
                "contact_id": self.mailing_contact.id,
                "list_id": self.mailing_list.id,
                "opt_out": True,
            }
        )
        self.assertFalse(subs.subscription_date)
        # Subscribe (opt_out = False)
        subs.opt_out = False
        self.assertTrue(subs.subscription_date)
