# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from datetime import date, datetime, timedelta
from openerp import api, fields, models


def message_post_with_view(records, views_or_xmlid, **kwargs):
    """ Method ported from mail.thread in v10 """
    values = kwargs.pop('values', None) or dict()
    try:
        from openerp.addons.website.models.website import slug
        values['slug'] = slug
    except ImportError:
        values['slug'] = lambda self: self.id
    if isinstance(views_or_xmlid, basestring):
        views = records.env.ref(views_or_xmlid, raise_if_not_found=False)
    else:
        views = views_or_xmlid
    if not views:
        return
    for record in records:
        values['object'] = record
        rendered_template = views.render(values, engine='ir.qweb')
        kwargs['body'] = rendered_template
        kwargs['message_type'] = 'notification'  # default in v10
        kwargs['subtype_id'] = record.env.ref('mail.mt_activities').id,
        record.message_post_with_template(False, **kwargs)


class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new
    activity_type_id field that indicates the activity linked to the message.
    """
    _name = 'mail.activity'
    _description = 'Activity'
    _order = 'date_deadline ASC'
    _rec_name = 'summary'

    @api.model
    def default_get(self, fields):
        res = super(MailActivity, self).default_get(fields)
        if not fields or 'res_model_id' in fields and res.get('res_model'):
            res['res_model_id'] = self.env['ir.model'].search([
                ('model', '=', res['res_model']),
            ]).id
        return res

    # owner
    res_id = fields.Integer('Related Document ID', index=True, required=True)
    res_model_id = fields.Many2one(
        'ir.model', 'Related Document Model',
        index=True, ondelete='cascade', required=True)
    res_model = fields.Char(
        'Related Document Model',
        index=True, related='res_model_id.model', store=True, readonly=True)
    res_name = fields.Char(
        'Document Name', compute='_compute_res_name', store=True,
        help="Display name of the related document.", readonly=True)
    # activity
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Activity',
        domain="['|', ('res_model_id', '=', False), "
        "('res_model_id', '=', res_model_id)]")
    activity_category = fields.Selection(related='activity_type_id.category')
    icon = fields.Char('Icon', related='activity_type_id.icon')
    summary = fields.Char('Summary')
    note = fields.Html('Note')
    feedback = fields.Html('Feedback')
    date_deadline = fields.Date(
        'Due Date', index=True, required=True, default=fields.Date.today,
    )
    # description
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        default=lambda self: self.env.user,
        index=True, required=True)
    state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], 'State',
        compute='_compute_state')
    recommended_activity_type_id = fields.Many2one(
        'mail.activity.type', string="Recommended Activity Type",
    )
    previous_activity_type_id = fields.Many2one(
        'mail.activity.type', string='Previous Activity Type',
    )
    has_recommended_activities = fields.Boolean(
        'Next activities available',
        compute='_compute_has_recommended_activities',
        help='Technical field for UX purpose')

    @api.multi
    @api.onchange('previous_activity_type_id')
    def _compute_has_recommended_activities(self):
        for record in self:
            record.has_recommended_activities = bool(
                record.previous_activity_type_id.next_type_ids
            )

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for activity in self:
            activity.res_name = self.env[activity.res_model].browse(
                activity.res_id
            ).name_get()[0][1]

    @api.depends('date_deadline')
    def _compute_state(self):
        today = date.today()
        for record in self.filtered(lambda activity: activity.date_deadline):
            date_deadline = fields.Date.from_string(record.date_deadline)
            diff = (date_deadline - today)
            if diff.days == 0:
                record.state = 'today'
            elif diff.days < 0:
                record.state = 'overdue'
            else:
                record.state = 'planned'

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id(self):
        if self.activity_type_id:
            self.summary = self.activity_type_id.summary
            self.date_deadline = (
                datetime.now() + timedelta(days=self.activity_type_id.days)
            )

    @api.onchange('previous_activity_type_id')
    def _onchange_previous_activity_type_id(self):
        if self.previous_activity_type_id.next_type_ids:
            self.recommended_activity_type_id =\
                self.previous_activity_type_id.next_type_ids[0]

    @api.onchange('recommended_activity_type_id')
    def _onchange_recommended_activity_type_id(self):
        self.activity_type_id = self.recommended_activity_type_id

    @api.model
    def create(self, values):
        activity = super(MailActivity, self).create(values)
        self.env[activity.res_model].browse(activity.res_id).message_subscribe(
            partner_ids=[activity.user_id.partner_id.id]
        )
        if activity.date_deadline <= fields.Date.today():
            self.env['bus.bus'].sendone(
                (
                    self._cr.dbname, 'res.partner',
                    activity.user_id.partner_id.id
                ),
                {'type': 'activity_updated', 'activity_created': True})
        return activity

    @api.multi
    def write(self, values):
        if values.get('user_id'):
            pre_responsibles = self.mapped('user_id.partner_id')
        res = super(MailActivity, self).write(values)
        if values.get('user_id'):
            for activity in self:
                self.env[activity.res_model].browse(
                    activity.res_id
                ).message_subscribe(
                    partner_ids=[activity.user_id.partner_id.id]
                )
                if activity.date_deadline <= fields.Date.today():
                    self.env['bus.bus'].sendone(
                        (
                            self._cr.dbname, 'res.partner',
                            activity.user_id.partner_id.id
                        ),
                        {'type': 'activity_updated', 'activity_created': True})
            for activity in self:
                if activity.date_deadline <= fields.Date.today():
                    for partner in pre_responsibles:
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner', partner.id),
                            {
                                'type': 'activity_updated',
                                'activity_deleted': True
                            }
                        )
        return res

    @api.multi
    def unlink(self):
        for activity in self:
            if activity.date_deadline <= fields.Date.today():
                self.env['bus.bus'].sendone(
                    (
                        self._cr.dbname, 'res.partner',
                        activity.user_id.partner_id.id
                    ),
                    {'type': 'activity_updated', 'activity_deleted': True})
        return super(MailActivity, self).unlink()

    @api.multi
    def action_done(self):
        """ Wrapper without feedback because web button add context as
        parameter, therefore setting context to feedback """
        return self.action_feedback()

    @api.multi
    def action_feedback(self, feedback=False):
        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            message_post_with_view(
                record,
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]

        self.unlink()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}
