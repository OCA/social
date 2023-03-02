# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    mass_mailing_contact_ids = fields.One2many(
        string="Mailing contacts",
        comodel_name="mailing.contact",
        inverse_name="partner_id",
    )
    mass_mailing_contacts_count = fields.Integer(
        string="Mailing contacts number",
        compute="_compute_mass_mailing_contacts_count",
        store=True,
        compute_sudo=True,
    )
    mass_mailing_stats_ids = fields.One2many(
        string="Mass mailing stats",
        comodel_name="mailing.trace",
        inverse_name="partner_id",
    )
    mass_mailing_stats_count = fields.Integer(
        string="Mass mailing stats number",
        compute="_compute_mass_mailing_stats_count",
        store=True,
    )

    @api.constrains("email")
    def _check_email_mass_mailing_contacts(self):
        for partner in self:
            if not partner.email and partner.sudo().mass_mailing_contact_ids:
                raise ValidationError(
                    _(
                        "This partner '%s' is linked to one or more mass "
                        "mailing contact. Email must be assigned."
                    )
                    % partner.name
                )

    @api.depends("mass_mailing_contact_ids")
    def _compute_mass_mailing_contacts_count(self):
        contact_data = self.env["mailing.contact"].read_group(
            [("partner_id", "in", self.ids)], ["partner_id"], ["partner_id"]
        )
        mapped_data = {
            contact["partner_id"][0]: contact["partner_id_count"]
            for contact in contact_data
        }
        for partner in self:
            partner.mass_mailing_contacts_count = mapped_data.get(partner.id, 0)

    @api.depends("mass_mailing_stats_ids")
    def _compute_mass_mailing_stats_count(self):
        contact_data = self.env["mailing.trace"].read_group(
            [("partner_id", "in", self.ids)], ["partner_id"], ["partner_id"]
        )
        mapped_data = {
            contact["partner_id"][0]: contact["partner_id_count"]
            for contact in contact_data
        }
        for partner in self:
            partner.mass_mailing_stats_count = mapped_data.get(partner.id, 0)

    def write(self, vals):
        res = super().write(vals)
        mm_vals = {}
        if vals.get("name"):
            mm_vals["name"] = vals["name"]
        if vals.get("email"):
            mm_vals["email"] = vals["email"]
        if vals.get("title"):
            mm_vals["title_id"] = vals["title"]
        if vals.get("company_id"):
            company = self.env["res.company"].browse(vals.get("company_id"))
            mm_vals["company_name"] = company.name
        if vals.get("country_id"):
            mm_vals["country_id"] = vals["country_id"]
        if mm_vals:
            # Using sudo because ACLs shouldn't produce data inconsistency
            self.env["mailing.contact"].sudo().search(
                [("partner_id", "in", self.ids)]
            ).write(mm_vals)
        return res
