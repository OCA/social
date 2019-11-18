# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mail.bounced.mixin"]

    # tracking_emails_count and email_score are non-store fields in order
    # to improve performance
    tracking_emails_count = fields.Integer(
        compute="_compute_email_score_and_count", readonly=True
    )
    email_score = fields.Float(compute="_compute_email_score_and_count", readonly=True)

    @api.depends("email")
    def _compute_email_score_and_count(self):
        partners_mail = self.filtered("email")
        mail_tracking_obj = self.env["mail.tracking.email"]
        for partner in partners_mail:
            partner.email_score = self.env[
                "mail.tracking.email"
            ].email_score_from_email(partner.email)
            partner.tracking_emails_count = mail_tracking_obj.search_count(
                [("recipient_address", "=", partner.email.lower())]
            )
        partners_no_mail = self - partners_mail
        partners_no_mail.update({"email_score": 50.0, "tracking_emails_count": 0})
