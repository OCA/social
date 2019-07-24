# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields, _, SUPERUSER_ID
from odoo.exceptions import ValidationError


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        res_model = self.env.context.get('default_res_model')
        model = self.env['ir.model'].search(
            [('model', '=', res_model)], limit=1)
        domain = [('member_ids', 'in', [user_id])]
        if res_model:
            domain.extend(['|', ('res_model_ids', '=', False),
                           ('res_model_ids', 'in', model.ids)])
        return self.env['mail.activity.team'].search(domain, limit=1)

    user_id = fields.Many2one(required=False)

    team_id = fields.Many2one(
        comodel_name='mail.activity.team',
        default=lambda s: s._get_default_team_id(),
    )

    @api.onchange('user_id')
    def _onchange_user_id(self):
        res = {'domain': {'team_id': []}}
        if not self.user_id:
            return res
        res['domain']['team_id'] = [
            '|',
            ('res_model_ids', '=', False),
            ('res_model_ids', 'in', self.res_model_id.ids)]
        if self.team_id and self.user_id in self.team_id.member_ids:
            return res
        self.team_id = self.with_context(
            default_res_model=self.res_model_id.id).\
            _get_default_team_id(user_id=self.user_id.id)
        return res

    @api.onchange('team_id')
    def _onchange_team_id(self):
        res = {'domain': {'user_id': []}}
        if not self.team_id:
            return res
        res['domain']['user_id'] = [('id', 'in', self.team_id.member_ids.ids)]
        if self.user_id not in self.team_id.member_ids:
            if self.team_id.user_id:
                self.user_id = self.team_id.user_id
            elif len(self.team_id.member_ids) == 1:
                self.user_id = self.team_id.member_ids
            else:
                self.user_id = self.env['res.users']
        return res

    @api.multi
    @api.constrains('team_id', 'user_id')
    def _check_team_and_user(self):
        for activity in self:
            # SUPERUSER is used to put mail.activity on some objects
            # like sale.order coming from stock.picking
            # (for example with exception type activity, with no backorder).
            # SUPERUSER is inactive and then even if you add it
            # to member_ids it's not taken account
            # To not be blocked we must add it to constraint condition
            if activity.user_id.id != SUPERUSER_ID and activity.team_id and \
                    activity.user_id and \
                    activity.user_id not in activity.team_id.member_ids:
                raise ValidationError(
                    _('The assigned user is not member of the team.'))

    @api.multi
    def action_create_calendar_event(self):
        res = super().action_create_calendar_event()
        res['context']['default_team_id'] = self.team_id.id or False
        return res
