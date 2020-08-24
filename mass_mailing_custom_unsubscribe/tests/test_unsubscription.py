# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase

from .. import exceptions


class UnsubscriptionCase(SavepointCase):
    def test_details_required(self):
        """Cannot create unsubscription without details when required."""
        with self.assertRaises(exceptions.DetailsRequiredError):
            self.env["mail.unsubscription"].create(
                {
                    "email": "axelor@yourcompany.example.com",
                    "mass_mailing_id": self.env.ref("mass_mailing.mass_mail_1").id,
                    "unsubscriber_id": "res.partner,%d"
                    % self.env.ref("base.res_partner_2").id,
                    "reason_id": self.env.ref(
                        "mass_mailing_custom_unsubscribe.reason_other"
                    ).id,
                }
            )

    def test_reason_required(self):
        """Cannot create unsubscription without reason when required."""
        with self.assertRaises(exceptions.ReasonRequiredError):
            self.env["mail.unsubscription"].create(
                {
                    "email": "axelor@yourcompany.example.com",
                    "mass_mailing_id": self.env.ref("mass_mailing.mass_mail_1").id,
                    "unsubscriber_id": "res.partner,%d"
                    % self.env.ref("base.res_partner_2").id,
                }
            )
