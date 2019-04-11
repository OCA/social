# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models

from ..status_constants import OFFLINE


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.multi
    def _compute_im_status(self):
        bus_recs = self.env['bus.presence'].search([
            ('partner_id', 'in', self.ids),
        ])
        statuses = bus_recs._get_partners_statuses()
        for record in self:
            record.im_status = statuses.get(record.id, OFFLINE)
