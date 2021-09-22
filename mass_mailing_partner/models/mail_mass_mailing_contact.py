# Copyright 2015 Tecnativa - Pedro M. Baeza
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner",
                                 domain=[('email', '!=', False)])

    @api.constrains('partner_id', 'list_ids')
    def _check_partner_id_list_ids(self):
        for contact in self:
            if contact.partner_id:
                other_contact = self.search([
                    ('partner_id', '=', contact.partner_id.id),
                    ('id', '!=', contact.id)
                ])
                if contact.list_ids & other_contact.mapped('list_ids'):
                    raise ValidationError(
                        _("Partner already exists in one of these "
                          "mailing lists") + ": %s" % contact.partner_id.display_name
                    )

    @api.onchange('partner_id')
    def _onchange_partner_mass_mailing_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.title_id = self.partner_id.title
            self.company_name = self.partner_id.company_id.name
            self.country_id = self.partner_id.country_id
            category_ids = self.partner_id.category_id
            if category_ids:
                self.tag_ids = category_ids

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            # Ensure that defaults are loaded (e.g.: import csv or xls)
            values_w_defaults = self.default_get(self._fields.keys())
            values_w_defaults.update(vals)
            record = self.new(values_w_defaults)
            if not record.partner_id:
                record._set_partner()
            record._onchange_partner_mass_mailing_partner()
            new_vals = record._convert_to_write(record._cache)
            new_vals.update(
                subscription_list_ids=values_w_defaults.get(
                    'subscription_list_ids', False),
                list_ids=values_w_defaults.get('list_ids', False)
            )
            new_vals_list.append(new_vals)
        return super().create(new_vals_list)

    def write(self, vals):
        for contact in self:
            new_vals = contact.copy_data(vals)[0]
            record = self.new(new_vals)
            if not record.partner_id:
                record._set_partner()
            record._onchange_partner_mass_mailing_partner()
            new_vals = record._convert_to_write(record._cache)
            new_vals.update(
                subscription_list_ids=vals.get('subscription_list_ids', False),
                list_ids=vals.get('list_ids', False)
            )
            super(MailMassMailingContact, contact).write(new_vals)
        return True

    def _get_categories(self):
        ca_ids = self.tag_ids.ids + self.list_ids.mapped('partner_category.id')
        return [[6, 0, ca_ids]]

    def _prepare_partner(self):
        return {
            'name': self.name or self.email,
            'email': self.email,
            'country_id': self.country_id.id,
            'title': self.title_id.id,
            'company_name': self.company_name,
            'category_id': self._get_categories(),
            'company_id': False,
        }

    @api.multi
    def _set_partner(self):
        self.ensure_one()
        m_partner = self.env['res.partner']
        # Look for a partner with that email
        email = self.email.strip()
        partner = m_partner.search([('email', '=ilike', email)], limit=1)
        if partner:
            # Partner found
            self.partner_id = partner
        else:
            lts = self.subscription_list_ids.mapped('list_id') | self.list_ids
            if lts.filtered('partner_mandatory'):
                # Create partner
                partner_vals = self._prepare_partner()
                self.partner_id = m_partner.sudo().create(partner_vals)
