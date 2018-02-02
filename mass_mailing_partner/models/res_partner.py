# -*- coding: utf-8 -*-
# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2017 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mass_mailing_contact_ids = fields.One2many(
        string="Mailing lists",
        oldname="mass_mailing_contacts",
        domain=[('opt_out', '=', False)],
        comodel_name='mail.mass_mailing.contact', inverse_name='partner_id')
    mass_mailing_contacts_count = fields.Integer(
        string='Mailing list number',
        compute='_compute_mass_mailing_contacts_count', store=True,
        compute_sudo=True)
    mass_mailing_stats = fields.One2many(
        string="Mass mailing stats",
        comodel_name='mail.mail.statistics', inverse_name='partner_id')
    mass_mailing_stats_count = fields.Integer(
        string='Mass mailing stats number',
        compute='_compute_mass_mailing_stats_count', store=True)

    @api.constrains('email')
    def _check_email_mass_mailing_contacts(self):
        for partner in self:
            if partner.sudo().mass_mailing_contact_ids and not partner.email:
                raise ValidationError(
                    _("This partner '%s' is subscribed to one or more "
                      "mailing lists. Email must be assigned.") % partner.name)

    @api.depends('mass_mailing_contact_ids',
                 'mass_mailing_contact_ids.opt_out')
    def _compute_mass_mailing_contacts_count(self):
        for reg in self:
            reg.mass_mailing_contacts_count = len(
                reg.mass_mailing_contact_ids)

    @api.depends('mass_mailing_stats')
    def _compute_mass_mailing_stats_count(self):
        for reg in self:
            reg.mass_mailing_stats_count = len(reg.mass_mailing_stats)

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if vals.get('name') or vals.get('email'):
            mm_vals = {}
            if vals.get('name'):
                mm_vals['name'] = vals['name']
            if vals.get('email'):
                mm_vals['email'] = vals['email']
            # Using sudo because ACLs shouldn't produce data inconsistency
            self.env["mail.mass_mailing.contact"].sudo().search([
                ("partner_id", "in", self.ids),
            ]).write(mm_vals)
        return res
