# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields, models


class MailActivityMixin(models.AbstractModel):
    """ Mail Activity Mixin is a mixin class to use if you want to add
    activities management on a model. It works like the mail.thread mixin. It
    defines an activity_ids one2many field toward activities using res_id and
    res_model_id.
    Various related / computed fields are also added to have a global status of
    activities on documents.

    Activities come with a new JS widget for the form view. It is integrated in
    the Chatter widget although it is a separate widget. It displays activities
    linked to the current record and allow to schedule, edit and mark done
    activities.
    Use widget="mail_activity" on activity_ids field in form view to use it.

    There is also a kanban widget defined. It defines a small widget to
    integrate in kanban vignettes. It allow to manage activities directly from
    the kanban view. Use widget="kanban_activity" on activitiy_ids field in
    kanban view to use it."""
    _name = 'mail.activity.mixin'
    _description = 'Activity Mixin'

    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        domain=lambda self: [('res_model', '=', self._name)])
    activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='State',
        compute='_compute_activity_state',
        help='Status based on activities\n'
        'Overdue: Due date is already passed\n'
        'Today: Activity date is today\nPlanned: Future activities.')
    activity_user_id = fields.Many2one(
        'res.users', 'Responsible',
        related='activity_ids.user_id',
        search='_search_activity_user_id')
    activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id',
        search='_search_activity_type_id')
    activity_date_deadline = fields.Date(
        'Next Activity Deadline', related='activity_ids.date_deadline',
        readonly=True, store=True)  # store to enable ordering + search
    activity_summary = fields.Char(
        'Next Activity Summary', related='activity_ids.summary',
        search='_search_activity_summary')

    @api.model
    def _setup_complete(self):
        """ Copied and disabled part of the method, since it doesn't work
            correctly for AbstractModels. Odoo fixed this for v10 and above
            in 92144ef """
        cls = type(self)

        ## set up field triggers
        #for field in cls._fields.itervalues():
        #    # dependencies of custom fields may not exist; ignore that case
        #    exceptions = (Exception,) if field.manual else ()
        #    with tools.ignore(*exceptions):
        #        field.setup_triggers(self.env)
        #
        ## add invalidation triggers on model dependencies
        #if cls._depends:
        #    for model_name, field_names in cls._depends.iteritems():
        #        model = self.env[model_name]
        #        for field_name in field_names:
        #            field = model._fields[field_name]
        #            for dependent in cls._fields.itervalues():
        #                model._field_triggers.add(field, (dependent, None))

        # determine old-api structures about inherited fields
        cls._inherits_reload()

        # register stuff about low-level function fields
        cls._init_function_fields(cls.pool, self._cr)

        # register constraints and onchange methods
        cls._init_constraints_onchanges()

        # check defaults
        for name in cls._defaults:
            assert name in cls._fields, \
                "Model %s has a default for nonexiting field %s" % (cls._name, name)

        # validate rec_name
        if cls._rec_name:
            assert cls._rec_name in cls._fields, \
                "Invalid rec_name %s for model %s" % (cls._rec_name, cls._name)
        elif 'name' in cls._fields:
            cls._rec_name = 'name'
        elif 'x_name' in cls._fields:
            cls._rec_name = 'x_name'

    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        for record in self:
            states = record.activity_ids.mapped('state')
            if 'overdue' in states:
                record.activity_state = 'overdue'
            elif 'today' in states:
                record.activity_state = 'today'
            elif 'planned' in states:
                record.activity_state = 'planned'

    @api.model
    def _search_activity_user_id(self, operator, operand):
        return [('activity_ids.user_id', operator, operand)]

    @api.model
    def _search_activity_type_id(self, operator, operand):
        return [('activity_ids.activity_type_id', operator, operand)]

    @api.model
    def _search_activity_summary(self, operator, operand):
        return [('activity_ids.summary', operator, operand)]

    @api.multi
    def unlink(self):
        """ Override unlink to delete records activities through
        (res_model, res_id). """
        record_ids = self.ids
        result = super(MailActivityMixin, self).unlink()
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result
