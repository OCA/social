# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo.tests.common import SavepointCase


class TestMailingPartnerContactActive(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mailing_contact = cls.env.ref("mass_mailing.mass_mail_contact_1")
        cls.partner = cls.env["res.partner"].create(
            cls.mailing_contact._prepare_partner()
        )
        cls.mailing_contact.write({"partner_id": cls.partner.id})

    def test_archive_unarchive_partner(self):
        self.assertTrue(self.partner.active)
        self.assertTrue(self.mailing_contact.active)
        self.partner.write({"active": False})
        self.assertFalse(self.partner.active)
        self.assertFalse(self.mailing_contact.active)
