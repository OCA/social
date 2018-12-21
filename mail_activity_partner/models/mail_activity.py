# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        index=True,
        compute='_compute_res_partner_id',
        store=True,
    )

    commercial_partner_id = fields.Many2one(
        related='partner_id.commercial_partner_id',
        string='Commercial Entity',
        store=True,
        related_sudo=True,
        readonly=True)

    @api.depends('res_model', 'res_id')
    def _compute_res_partner_id(self):
        for obj in self:
            res_model = obj.res_model
            res_id = obj.res_id
            if res_model == 'res.partner':
                obj.partner_id = res_id
            else:
                res_model_id = obj.env[res_model].search([('id', '=', res_id)])
                if 'partner_id' in res_model_id._fields and \
                        res_model_id.partner_id:
                    obj.partner_id = res_model_id.partner_id
                else:
                    obj.partner_id = None
