# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from openerp import api, models, fields


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def default_get(self, fields):
        if self.env.context.get('default_res_model') and not \
                self.env.context.get('default_res_model_id'):
            self = self.with_context(
                default_res_model_id=self.env['ir.model'].sudo().search([
                    ('model', '=', self.env.context['default_res_model'])
                ], limit=1).id
            )
        defaults = super(CalendarEvent, self).default_get(fields)

        # support active_model / active_id as replacement of
        # default_* if not already given
        if 'res_model_id' not in defaults and 'res_model_id' in fields and \
                self.env.context.get('active_model') and \
                self.env.context['active_model'] != 'calendar.event':
            defaults['res_model_id'] = self.env['ir.model'].sudo().search(
                [('model', '=', self.env.context['active_model'])],
                limit=1).id
        if 'res_id' not in defaults and 'res_id' in fields and \
                defaults.get(
                    'res_model_id') and self.env.context.get('active_id'):
            defaults['res_id'] = self.env.context['active_id']

        return defaults

    # linked document
    res_id = fields.Integer('Document ID')
    res_model_id = fields.Many2one('ir.model',
                                   'Document Model', ondelete='cascade')
    res_model = fields.Char('Document Model Name',
                            related='res_model_id.model', readonly=True,
                            store=True)
    activity_ids = fields.One2many('mail.activity', 'calendar_event_id',
                                   string='Activities')

    @api.model
    def create(self, values):
        # created from calendar: try to create an activity
        # on the related record
        if not values.get('activity_ids'):
            defaults = self.default_get(['activity_ids',
                                         'res_model_id', 'res_id', 'user_id'])
            res_model_id = values.get('res_model_id', defaults.get(
                'res_model_id'))
            res_id = values.get('res_id', defaults.get('res_id'))
            user_id = values.get('user_id', defaults.get('user_id'))
            if not defaults.get('activity_ids') and res_model_id and res_id:
                if hasattr(self.env[self.env['ir.model'].sudo().browse(
                        res_model_id).model], 'activity_ids'):
                    meeting_activity_type = \
                        self.env['mail.activity.type'].search(
                            [('category', '=', 'meeting')], limit=1)
                    if meeting_activity_type:
                        activity_vals = {
                            'res_model_id': res_model_id,
                            'res_id': res_id,
                            'activity_type_id': meeting_activity_type.id,
                        }
                        if user_id:
                            activity_vals['user_id'] = user_id
                        values['activity_ids'] = [(0, 0, activity_vals)]

        meeting = super(CalendarEvent, self).create(values)
        meeting._sync_activities(values)
        return meeting

    @api.multi
    def write(self, values):
        # compute duration, only if start and stop are modified
        if 'duration' not in values and 'start' in values and 'stop' in values:
            values['duration'] = self._get_duration(values['start'],
                                                    values['stop'])

        self._sync_activities(values)
        return super(CalendarEvent, self).write(values)

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_done(self):
        for rec in self:
            rec.activity_ids.action_feedback()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_open_calendar_event(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(
                self.res_id).get_formview_action()[0]
        return False

    def _sync_activities(self, values):
        # update activities
        if self.mapped('activity_ids'):
            activity_values = {}
            if values.get('name'):
                activity_values['summary'] = values['name']
            if values.get('description'):
                activity_values['note'] = values['description']
            if values.get('start'):
                activity_values['date_deadline'] = \
                    fields.Datetime.from_string(values['start']).date()
            if values.get('user_id'):
                activity_values['user_id'] = values['user_id']
            if activity_values.keys():
                self.mapped('activity_ids').write(activity_values)
