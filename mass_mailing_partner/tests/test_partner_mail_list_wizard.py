# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError

from . import base


class PartnerMailListWizardCase(base.BaseCase):
    def test_add_to_mail_list(self):
        wizard = self.env["partner.mail.list.wizard"].create(
            {"mail_list_id": self.mailing_list.id}
        )
        wizard.partner_ids = [self.partner.id]
        wizard.add_to_mail_list()
        contacts = self.env["mailing.contact"].search(
            [("partner_id", "=", self.partner.id)]
        )
        cont = contacts.filtered(lambda r: wizard.mail_list_id in r.list_ids)
        self.assertEqual(len(cont), 1)
        self.check_mailing_contact_partner(cont)
        # This line does not create a new contact
        wizard.add_to_mail_list()
        self.assertEqual(len(self.partner.mass_mailing_contact_ids), 1)
        self.assertEqual(
            self.partner.mass_mailing_contact_ids.list_ids, self.mailing_list
        )

        list_2 = self.create_mailing_list({"name": "Test Add to List"})
        wizard.mail_list_id = list_2
        wizard.add_to_mail_list()
        self.assertEqual(len(self.partner.mass_mailing_contact_ids), 1)
        self.assertEqual(
            self.partner.mass_mailing_contact_ids.list_ids, self.mailing_list | list_2
        )

        partner = self.env["res.partner"].create({"name": "No email partner"})
        wizard.partner_ids = [partner.id]
        with self.assertRaises(UserError):
            wizard.add_to_mail_list()
