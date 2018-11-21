# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from openerp import fields, models


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a
    different kind of activity e.g. call, mail, meeting. An activity can be
    generic i.e. available for all models using activities; or specific to a
    model in which case res_model_id field should be used. """
    _name = 'mail.activity.type'
    _description = 'Activity Type'
    _rec_name = 'name'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    summary = fields.Char('Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    days = fields.Integer(
        '# Days', default=0,
        help='Number of days before executing the action. It allows to plan '
        'the action deadline.')
    icon = fields.Char('Icon', help="Font awesome icon e.g. fa-tasks")
    res_model_id = fields.Many2one(
        'ir.model', 'Model', index=True,
        help='Specify a model if the activity should be specific to a model'
             'and not available when managing activities for other models.')
    next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id',
        'recommended_id', string='Recommended Next Activities')
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id',
        'activity_id', string='Preceding Activities')
    category = fields.Selection([
        ('default', 'Other')], default='default',
        string='Category',
        help='Categories may trigger specific behavior like opening calendar '
        'view')
