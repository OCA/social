# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    mailing_contact_id = fields.Many2one(
        comodel_name="mailing.contact",
        string="Mass Mailing Contact",
        help="The mailing list contact that matches this partner's email.",
        compute="_compute_mailing_contact_id",
        store=True,
    )

    @api.depends("email_normalized")
    def _compute_mailing_contact_id(self):
        # Unique list of normalized email addresses
        emails = {m for m in self.mapped("email_normalized") if m}
        if not emails:
            self.mailing_contact_id = False
            return
        query = """
            SELECT email_normalized, id
            FROM mailing_contact
            WHERE email_normalized IN %s
        """
        self.env["mailing.contact"].flush(["email_normalized"])
        self.env.cr.execute(query, (tuple(emails),))
        mailing_contact_id_by_email = dict(self.env.cr.fetchall())
        for rec in self:
            rec.mailing_contact_id = mailing_contact_id_by_email.get(
                rec.email_normalized
            )
