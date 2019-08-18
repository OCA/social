# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AutoSubscribeNotifyOwnModel(models.Model):
    _name = 'auto.subscribe.notify.own.model'

    name = fields.Char(compute='_compute_name')
    model_id = fields.Many2one('ir.model', 'Model', required=True)
    active = fields.Boolean(default=True)

    @api.multi
    @api.depends('model_id')
    def _compute_name(self):
        for record in self:
            record.name = record.model_id.model
