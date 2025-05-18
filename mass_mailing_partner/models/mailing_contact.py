# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# Copyright 2020 Tecnativa - Manuel Calero
# Copyright 2020 Hibou Corp.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailingContact(models.Model):
    _inherit = "mailing.contact"

    partner_id = fields.Many2one(
        comodel_name="res.partner", string="Partner", domain=[("email", "!=", False)]
    )
    tag_ids = fields.Many2many(compute="_compute_tag_ids", store=True)

    @api.depends("partner_id", "partner_id.category_id")
    def _compute_tag_ids(self):
        for rec in self:
            tags = rec.tag_ids
            if rec.partner_id.category_id:
                tags = rec.partner_id.category_id
            rec.tag_ids = tags

    @api.constrains("partner_id", "list_ids")
    def _check_partner_id_list_ids(self):
        for contact in self:
            if contact.partner_id:
                other_contact = self.search(
                    [
                        ("partner_id", "=", contact.partner_id.id),
                        ("id", "!=", contact.id),
                    ]
                )
                if contact.list_ids & other_contact.mapped("list_ids"):
                    raise ValidationError(
                        _("Partner already exists in one of these mailing lists")
                        + ": %s" % contact.partner_id.display_name
                    )

    def update_fields_based_on_partner(self):
        for rec in self.filtered("partner_id"):
            rec.name = rec.partner_id.name
            rec.email = rec.partner_id.email
            rec.title_id = rec.partner_id.title
            rec.company_name = (
                rec.partner_id.company_id.name or rec.partner_id.company_name
            )
            rec.country_id = rec.partner_id.country_id

    @api.onchange("partner_id")
    def _onchange_partner_mass_mailing_partner(self):
        self.update_fields_based_on_partner()

    def _overwrite_partner(self, vals, creating=False):
        """Overwrite partner and update contact data if needed."""
        self.ensure_one()
        if self.env.context.get("mass_mailing_partner_writing"):
            return
        _self = self.with_context(mass_mailing_partner_writing=True)
        prev_partner = _self.partner_id
        if "partner_id" not in vals:
            _self._set_partner()
        if creating or prev_partner != _self.partner_id:
            _self.update_fields_based_on_partner()

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        for contact, vals in zip(result, vals_list):
            contact._overwrite_partner(vals, True)
        return result

    def _get_categories(self):
        ca_ids = (
            self.tag_ids.ids
            + self.list_ids.mapped("partner_category.id")
            + self.subscription_list_ids.mapped("list_id.partner_category.id")
        )
        return [[6, 0, ca_ids]]

    def _prepare_partner(self):
        return {
            "name": self.name or self.email,
            "email": self.email,
            "country_id": self.country_id.id,
            "title": self.title_id.id,
            "company_name": self.company_name,
            "company_id": False,
            "category_id": self._get_categories(),
        }

    def _set_partner(self):
        self.ensure_one()
        if not self.email:
            return
        m_partner = self.env["res.partner"]
        # Look for a partner with that email
        email = self.email.strip()
        if email == self.partner_id.email:
            return
        partner = m_partner.search([("email", "=ilike", email)], limit=1)
        if partner:
            if partner == self.partner_id:
                return
            # Partner found
            self.partner_id = partner
        else:
            lts = self.subscription_list_ids.mapped("list_id") | self.list_ids
            if lts.filtered("partner_mandatory"):
                # Create partner
                partner_vals = self._prepare_partner()
                self.partner_id = m_partner.sudo().create(partner_vals)
