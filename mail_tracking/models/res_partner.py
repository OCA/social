# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mail.bounced.mixin"]

    # email_score is a non-store field in order to improve performance
    email_score = fields.Float(compute="_compute_email_score_and_count", readonly=True)

    @api.depends("email")
    def _compute_email_score_and_count(self):
        self.email_score = 50.0
        partners_mail = self.filtered("email")
        mt_obj = self.env["mail.tracking.email"].sudo()
        for partner in partners_mail:
            partner.email_score = mt_obj.email_score_from_email(partner.email)
