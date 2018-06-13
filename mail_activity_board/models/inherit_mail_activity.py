# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
# SDI
# author: djuaneda@sdi.es
from odoo import api, models, fields, tools, _
from odoo.tools.safe_eval import safe_eval

class MailActivity(models.Model):
    _inherit = "mail.activity"

    res_model_id_name = fields.Char(
        default="", related='res_model_id.name',
        string="Origin", store=False, readonly=True)
    duration = fields.Float(
        related='calendar_event_id.duration',
        string="Duration", store=False, readonly=True)
    calendar_event_id_start = fields.Datetime(
        default=False, related='calendar_event_id.start',
        store=False, readonly=True)
    calendar_event_id_partner_ids = fields.Many2many(
        related='calendar_event_id.partner_ids', string='Attendees',
        store=False, default=False,readonly=True)

    @api.multi
    def open_origin(self):
        """
        Utility method used to add an "Open Company" button in partner views.
        """
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
    def action_your_activities(self):
        action = self.env.ref('mail_activity_board.open_boards_activities_form_tree').read()[0]
        action_context = safe_eval(action['context'], {'uid': self.env.uid})
        action['context'] = action_context
        return action
