# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestCompanyNewsletter(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner_a = cls.env["res.partner"].create(
            {
                "name": "Contact A",
                "email": "a@example.com",
            }
        )
        cls.partner_b = cls.env["res.partner"].create(
            {
                "name": "Contact B",
                "email": "b@example.com",
            }
        )
        cls.partner_b_2 = cls.env["res.partner"].create(
            {
                "name": "Contact B2 (Same email than B)",
                "email": "b@example.com",
            }
        )

    def test_01_default_mailing_list(self):
        self.assertTrue(
            self.env.company.main_mailing_list_id,
            "Set through default value",
        )

    def test_02_partner_subscription_workflow(self):
        # Subscribe Partner A
        # This should CREATE the subscription record
        self.partner_a.main_mailing_list_subscription_state = "subscribed"
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id)
        self.assertFalse(self.partner_a.main_mailing_list_subscription_id.opt_out)
        # # Unsubscribe Partner A
        # This should UPDATE the subscription record
        self.partner_a.main_mailing_list_subscription_state = "unsubscribed"
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id)
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id.opt_out)
        # Subscribe Partner A
        # This should UPDATE the subscription record
        self.partner_a.main_mailing_list_subscription_state = "subscribed"
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id)
        self.assertFalse(self.partner_a.main_mailing_list_subscription_id.opt_out)
        # Set back to False (should remove subscribtion record)
        self.partner_a.main_mailing_list_subscription_state = False
        self.assertFalse(self.partner_a.main_mailing_list_subscription_id)
        # Unsubscribe Partner A
        # This should CREATE the subscription record, opted out
        self.partner_a.main_mailing_list_subscription_state = "unsubscribed"
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id)
        self.assertTrue(self.partner_a.main_mailing_list_subscription_id.opt_out)

    def test_03_partner_subscription_workflow_same_email(self):
        # Subscribe Partner B, but check Partner B 2 (same email = same subscription)
        self.partner_b.main_mailing_list_subscription_state = "subscribed"
        self.assertTrue(self.partner_b_2.main_mailing_list_subscription_id)
        self.assertFalse(self.partner_b_2.main_mailing_list_subscription_id.opt_out)
        # Unsubscribe Partner B
        self.partner_b.main_mailing_list_subscription_state = "unsubscribed"
        self.assertTrue(self.partner_b_2.main_mailing_list_subscription_id)
        self.assertTrue(self.partner_b_2.main_mailing_list_subscription_id.opt_out)
        # Set back to False (should remove subscribtion record)
        self.partner_b.main_mailing_list_subscription_state = False
        self.assertFalse(self.partner_b_2.main_mailing_list_subscription_id)

    def test_04_search_partner_subscription(self):
        # Partner A is not subscribed (field is empty)
        empty_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", False),
            ]
        )
        self.assertTrue(empty_partners & self.partner_a)
        # Subscribe Partner A
        self.partner_a.main_mailing_list_subscription_state = "subscribed"
        subscribed_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", "subscribed"),
            ]
        )
        unsubscribed_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", "unsubscribed"),
            ]
        )
        empty_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", False),
            ]
        )
        self.assertTrue(subscribed_partners & self.partner_a)
        self.assertFalse(unsubscribed_partners & self.partner_a)
        self.assertFalse(empty_partners & self.partner_a)
        # Unsubscribe Partner A
        self.partner_a.main_mailing_list_subscription_state = "unsubscribed"
        subscribed_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", "subscribed"),
            ]
        )
        unsubscribed_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", "unsubscribed"),
            ]
        )
        empty_partners = self.env["res.partner"].search(
            [
                ("main_mailing_list_subscription_state", "=", False),
            ]
        )
        self.assertFalse(subscribed_partners & self.partner_a)
        self.assertTrue(unsubscribed_partners & self.partner_a)
        self.assertFalse(empty_partners & self.partner_a)

    def test_05_partner_subscription_state(self):
        # Partner is not subscribed
        self.assertFalse(self.partner_a.main_mailing_list_subscription_state)
        # Subscribe
        main_mailing_list = self.env.company.main_mailing_list_id
        contact = self.env["mailing.contact"].create(
            {
                "name": self.partner_a.name,
                "email": self.partner_a.email,
            }
        )
        subs = self.env["mailing.contact.subscription"].create(
            {
                "contact_id": contact.id,
                "list_id": main_mailing_list.id,
            }
        )
        self.assertEqual(
            self.partner_a.main_mailing_list_subscription_state,
            "subscribed",
        )
        # Opt out
        subs.opt_out = True
        self.assertEqual(
            self.partner_a.main_mailing_list_subscription_state,
            "unsubscribed",
        )
