# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models, fields


class MailActivity(models.Model):
    _inherit = "mail.activity"

    res_model_id_name = fields.Char(
        related='res_model_id.name', string="Origin",
        readonly=True)
    duration = fields.Float(
        related='calendar_event_id.duration', readonly=True)
    calendar_event_id_start = fields.Datetime(
        related='calendar_event_id.start', readonly=True)
    calendar_event_id_partner_ids = fields.Many2many(
        related='calendar_event_id.partner_ids',
        Stringreadonly=True)

    @api.multi
    def open_origin(self):
        self.ensure_one()
        response = {'type': 'ir.actions.act_window',
                    'res_model': self.res_model,
                    'view_mode': 'form',
                    'res_id': self.res_id,
                    'target': 'current',
                    'flags': {'form': {'action_buttons': False}}}
        if self.res_model == 'crm.lead':
            res_type = self.env['crm.lead'].browse(self.res_id).type
            if res_type == 'opportunity':
                view_id = self.env.ref("crm.crm_case_form_view_oppor").id
                response['view_id'] = view_id
        return response

    @api.model
    def action_activities_board(self):
        action = self.env.ref(
            'mail_activity_board.open_boards_activities').read()[0]
        return action
