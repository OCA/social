# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_default_team_id(self):
        res_model = self.env.context.get('default_res_model', False)
        model = self.env['ir.model'].search([('model', '=', res_model)],
                                            limit=1)
        domain = [('member_ids', 'in', [self.env.uid])]
        if res_model:
            domain.extend(['|', ('res_model_ids', '=', False),
                           ('res_model_ids', 'in', model.ids)])
        return self.env['mail.activity.team'].search(domain, limit=1)

    team_id = fields.Many2one('mail.activity.team',
                              default=lambda s: s._get_default_team_id(),)

    @api.onchange('res_model_id', 'user_id')
    def _onchange_model_user(self):
        res = {'domain': {'team_id': []}}
        if self.team_id:
            if self.user_id not in self.team_id.member_ids:
                self.team_id = False
        if self.res_model_id:
            res['domain']['team_id'] = [
                ('res_model_ids', 'in', self.res_model_id.ids)]
        if self.user_id:
            res['domain']['team_id'] = [
                ('member_ids', 'in', self.user_id.ids)]
        return res
