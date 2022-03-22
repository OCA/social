# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo.tests.common import SavepointCase


class TestMailingContactActive(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_contact = cls.env.ref("mass_mailing.mass_mail_contact_1")

    def test_archive_unarchive_mailing_contact(self):
        self.assertTrue(self.mailing_contact.active)
        subscription = self.mailing_contact.subscription_list_ids
        self.assertTrue(subscription)
        self.assertTrue(subscription.active)
        self.mailing_contact.write({"active": False})
        self.assertFalse(self.mailing_contact.active)
        self.assertFalse(subscription.active)
