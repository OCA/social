# -*- coding: utf-8 -*-
# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner",
                                 domain=[('email', '!=', False)])

    @api.constrains('partner_id')
    def _check_partner_id(self):
        if self.search([
            ('id', '!=', self.id),
            ('partner_id', '=', self.partner_id.id),
        ]):
            raise ValidationError(
                "Partner already exists in this mailing list.")

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email

    @api.model
    @api.returns('self', lambda x: x.id)
    def create(self, vals):
        if not vals.get('partner_id'):
            vals = self._set_partner(vals)
        vals = self._set_name_email(vals)
        return super(MailMassMailingContact, self).create(vals)

    def write(self, vals):
        for contact in self:
            if vals.get('partner_id', None) is False:
                # If removing partner, search again by email
                vals = contact._set_partner(vals)
            vals = contact._set_name_email(vals)
        return super(MailMassMailingContact, self).write(vals)

    def _prepare_partner(self, vals, mailing_list):
        vals = {
            'name': vals.get('name') or vals.get('email'),
            'email': vals.get('email', False),
        }
        if mailing_list.partner_category:
            vals['category_id'] = [(4, mailing_list.partner_category.id, 0)]
        return vals

    def _set_partner(self, vals):
        email = vals.get('email', self.email)
        if not email:  # pragma: no cover
            return vals
        m_mailing = self.env['mail.mass_mailing.list']
        m_partner = self.env['res.partner']
        list_ids = vals.get('list_ids', self.list_ids.ids)
        mailing_list = m_mailing.browse(list_ids)
        # Look for a partner with that email
        email = email.strip()
        partners = m_partner.search([('email', '=ilike', email)], limit=1)
        if partners:
            # Partner found
            vals['partner_id'] = partners[0].id
        elif mailing_list.partner_mandatory:
            # Create partner
            partner = m_partner.sudo().create(
                self._prepare_partner(vals, mailing_list))
            vals['partner_id'] = partner.id
        return vals

    def _set_name_email(self, vals):
        partner_id = vals.get('partner_id', self.partner_id.id)
        if not partner_id:
            return vals
        partner = self.env['res.partner'].browse(partner_id)
        vals['email'] = partner.email
        vals['name'] = partner.name
        return vals
