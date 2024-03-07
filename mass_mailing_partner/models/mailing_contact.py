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

    @api.onchange("partner_id")
    def _onchange_partner_mass_mailing_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.title_id = self.partner_id.title
            self.company_name = (
                self.partner_id.company_id.name or self.partner_id.company_name
            )
            self.country_id = self.partner_id.country_id

    @api.model
    def _get_contact_vals(self, origin_vals):
        record = self.new(origin_vals)
        if not record.partner_id:
            record._set_partner()
        record._onchange_partner_mass_mailing_partner()
        new_vals = record._convert_to_write(record._cache)
        new_vals.update(
            subscription_ids=origin_vals.get("subscription_ids", []),
            list_ids=origin_vals.get("list_ids", []),
        )
        if new_vals.get("partner_id") and "tag_ids" in new_vals:
            # When there is a partner, tag_ids must get value from the compute function
            # otherwise, its values will be different from partner
            del new_vals["tag_ids"]
        return new_vals

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            new_vals = self._get_contact_vals(vals)
            new_vals_list.append(new_vals)
        return super().create(new_vals_list)

    def write(self, vals):
        for contact in self:
            origin_vals = contact.copy_data(vals)[0]
            new_vals = self._get_contact_vals(origin_vals)
            super(MailingContact, contact).write(new_vals)
        return True

    def _get_categories(self):
        ca_ids = (
            self.tag_ids.ids
            + self.list_ids.mapped("partner_category.id")
            + self.subscription_ids.mapped("list_id.partner_category.id")
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
        partner = m_partner.search([("email", "=ilike", email)], limit=1)
        if partner:
            # Partner found
            self.partner_id = partner
        else:
            lts = self.subscription_ids.mapped("list_id") | self.list_ids
            if lts.filtered("partner_mandatory"):
                # Create partner
                partner_vals = self._prepare_partner()
                self.partner_id = m_partner.sudo().create(partner_vals)
