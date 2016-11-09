# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import copy
from openerp import models, fields, api


def event_filtered_ids(model, mass_mailing_id, domain, field='email'):
    field = field or 'email'
    domain = domain or []
    exclude_emails = []
    mass_mailing = model.env['mail.mass_mailing'].browse(mass_mailing_id)
    if mass_mailing.event_id:
        exclude = mass_mailing.exclude_event_state_ids.mapped('code')
        reg_domain = False
        registrations = model.env['event.registration']
        if exclude:
            reg_domain = [
                ('event_id', '=', mass_mailing.event_id.id),
                ('state', 'in', exclude)
            ]
        if reg_domain:
            registrations = registrations.search(reg_domain)
        if registrations:
            exclude_emails = registrations.mapped('email')
    apply_domain = copy.deepcopy(domain)
    if exclude_emails:
        apply_domain.append((field, 'not in', exclude_emails))
    rows = model.search(apply_domain)
    return rows.ids


class MailMassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    def _default_exclude_event_state_ids(self):
        return self.env['event.registration.state'].search([])

    event_id = fields.Many2one(
        string="Event related", comodel_name='event.event')
    exclude_event_state_ids = fields.Many2many(
        comodel_name='event.registration.state',
        string="Exclude", default=_default_exclude_event_state_ids)

    @api.model
    def get_recipients(self, mailing):
        res_ids = super(MailMassMailing, self).get_recipients(mailing)
        if res_ids:
            domain = [('id', 'in', res_ids)]
            return event_filtered_ids(
                self.env[mailing.mailing_model], mailing.id, domain,
                field='email')
        return res_ids
