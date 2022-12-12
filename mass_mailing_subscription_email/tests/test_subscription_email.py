# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase

from odoo.addons.mail.tests.common import MockEmail


class TestSubscriptionEmail(SavepointCase, MockEmail):
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
        module_name = "mass_mailing_subscription_email"
        cls.subscribe_tmpl = cls.env.ref(f"{module_name}.mailing_list_subscribe")
        cls.unsubscribe_tmpl = cls.env.ref(f"{module_name}.mailing_list_unsubscribe")
        # Set some tmpl values to ease tests
        cls.email_from = "your-company@example.com"
        cls.subscribe_tmpl.email_from = cls.email_from
        cls.subscribe_tmpl.subject = "SUBSCRIBED"
        cls.unsubscribe_tmpl.email_from = cls.email_from
        cls.unsubscribe_tmpl.subject = "UNSUBSCRIBED"

    def test_subscription_email(self):
        # Create subscription
        with self.mock_mail_gateway():
            subs = self.env["mailing.contact.subscription"].create(
                {
                    "contact_id": self.mailing_contact.id,
                    "list_id": self.mailing_list.id,
                }
            )
        self.assertEqual(self._new_mails.email_from, self.email_from)
        self.assertEqual(self._new_mails.email_to, self.mailing_contact.email)
        self.assertEqual(self._new_mails.subject, "SUBSCRIBED")
        # Unsubscribe
        with self.mock_mail_gateway():
            subs.opt_out = True
        self.assertEqual(self._new_mails.email_from, self.email_from)
        self.assertEqual(self._new_mails.email_to, self.mailing_contact.email)
        self.assertEqual(self._new_mails.subject, "UNSUBSCRIBED")
        # Unsubscribe again (even though it's already unsubscribed)
        with self.mock_mail_gateway():
            subs.opt_out = True
        self.assertFalse(self._new_mails)
        # Subscribe again
        with self.mock_mail_gateway():
            subs.opt_out = False
        self.assertEqual(self._new_mails.email_from, self.email_from)
        self.assertEqual(self._new_mails.email_to, self.mailing_contact.email)
        self.assertEqual(self._new_mails.subject, "SUBSCRIBED")
        # Unsubscribe through unlinking
        with self.mock_mail_gateway():
            subs.unlink()
        self.assertEqual(self._new_mails.email_from, self.email_from)
        self.assertEqual(self._new_mails.email_to, self.mailing_contact.email)
        self.assertEqual(self._new_mails.subject, "UNSUBSCRIBED")

    def test_subscription_email_no_repetition(self):
        """No email must be sent if it's created and opted out at the same time"""
        with self.mock_mail_gateway():
            subs = self.env["mailing.contact.subscription"].create(
                {
                    "contact_id": self.mailing_contact.id,
                    "list_id": self.mailing_list.id,
                    "opt_out": True,
                }
            )
        self.assertFalse(self._new_mails)
        # Even after re-writing on the field
        with self.mock_mail_gateway():
            subs.opt_out = True
        self.assertFalse(self._new_mails)
        # Subscribing must send the email
        with self.mock_mail_gateway():
            subs.opt_out = False
        self.assertEqual(self._new_mails.email_from, self.email_from)
        self.assertEqual(self._new_mails.email_to, self.mailing_contact.email)
        self.assertEqual(self._new_mails.subject, "SUBSCRIBED")
        # Subscribing again mustn't..
        with self.mock_mail_gateway():
            subs.opt_out = False
        self.assertFalse(self._new_mails)

    def test_subscription_email_disabled(self):
        self.mailing_list.subscribe_template_id = False
        self.mailing_list.unsubscribe_template_id = False
        # Create subscription
        with self.mock_mail_gateway():
            subs = self.env["mailing.contact.subscription"].create(
                {
                    "contact_id": self.mailing_contact.id,
                    "list_id": self.mailing_list.id,
                }
            )
        self.assertFalse(self._new_mails)
        # Unsubscribe
        with self.mock_mail_gateway():
            subs.opt_out = True
        self.assertFalse(self._new_mails)
        # Subscribe again
        with self.mock_mail_gateway():
            subs.opt_out = False
        self.assertFalse(self._new_mails)
        # Unsubscribe through unlinking
        with self.mock_mail_gateway():
            subs.unlink()
        self.assertFalse(self._new_mails)

    def test_skip_subscription_email_context(self):
        # Create subscription
        with self.mock_mail_gateway():
            Subscription = self.env["mailing.contact.subscription"]
            Subscription.with_context(skip_subscription_email=True).create(
                {
                    "contact_id": self.mailing_contact.id,
                    "list_id": self.mailing_list.id,
                }
            )
        self.assertFalse(self._new_mails)
