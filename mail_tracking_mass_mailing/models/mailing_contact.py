# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class MailMassMailingContact(models.Model):
    _name = "mailing.contact"
    _inherit = ["mailing.contact", "mail.bounced.mixin"]

    email_score = fields.Float(
        string="Email score", readonly=True, store=False, compute="_compute_email_score"
    )

    @api.depends("email")
    def _compute_email_score(self):
        with_email = self.filtered("email")
        for contact in with_email:
            contact.email_score = self.env[
                "mail.tracking.email"
            ].email_score_from_email(contact.email)
        remaining = self - with_email
        remaining.email_score = 0.0
