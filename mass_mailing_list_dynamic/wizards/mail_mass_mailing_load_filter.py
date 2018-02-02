# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MassMailingLoadFilter(models.TransientModel):
    _name = "mail.mass_mailing.load.filter"

    filter_id = fields.Many2one(
        comodel_name='ir.filters',
        string="Filter to load",
        required=True,
        domain=[('model_id', '=', 'res.partner')],
    )

    def load_filter(self):
        self.ensure_one()
        mass_list = self.env['mail.mass_mailing.list'].browse(
            self.env.context['active_id']
        )
        mass_list.sync_domain = self.filter_id.domain
