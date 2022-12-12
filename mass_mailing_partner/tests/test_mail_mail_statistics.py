# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from . import base


class MailMailStatisticsCase(base.BaseCase):
    def test_link_partner(self):
        partner = self.create_partner({"name": "Test partner"})
        stat = self.env["mailing.trace"].create(
            {"model": "res.partner", "res_id": partner.id}
        )
        self.assertEqual(partner.id, stat.partner_id.id)

    def test_link_mail_contact(self):
        partner = self.create_partner(
            {"name": "Test partner", "email": "test@domain.com"}
        )
        contact_vals = {
            "partner_id": partner.id,
            "list_ids": [[6, 0, [self.mailing_list.id]]],
        }
        contact = self.create_mailing_contact(contact_vals)
        stat = self.env["mailing.trace"].create(
            {"model": "mailing.contact", "res_id": contact.id}
        )
        self.assertEqual(partner.id, stat.partner_id.id)
