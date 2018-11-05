# -*- coding: utf-8 -*-
# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class MailMassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner",
                                 domain=[('email', '!=', False)])

    _sql_constraints = [
        ('partner_list_uniq', 'unique(partner_id, list_id)',
         _('Partner already exists in this mailing list.'))
    ]

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
        remaining = self
        for contact in self:
            _vals = vals.copy()
            # If removing partner, search again by email
            if _vals.get('partner_id') is False:
                _vals = contact._set_partner(_vals)
            _vals = contact._set_name_email(_vals)
            # If changed, write it separately
            if vals != _vals:
                remaining -= contact
                super(MailMassMailingContact, contact).write(_vals)
        # Normal batch write for contacts that need no customization
        return super(MailMassMailingContact, remaining).write(vals)

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
        list_id = vals.get('list_id', self.list_id.id)
        mailing_list = m_mailing.browse(list_id, prefetch=self._prefetch)
        # Look for a partner with that email
        email = email.strip()
        partner = m_partner.search([('email', '=ilike', email)], limit=1)
        # Different partner found
        if partner and partner != self.partner_id:
            vals['partner_id'] = partner.id
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
        partner = self.env['res.partner'].browse(
            partner_id, prefetch=self._prefetch)
        if vals.get("email", self.email) != partner.email:
            vals['email'] = partner.email
        if vals.get("name", self.name) != partner.name:
            vals['name'] = partner.name
        return vals
