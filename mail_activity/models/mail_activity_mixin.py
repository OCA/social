# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, fields


def setup_mail_actitivities(cls):
    """ Mixin using AbstractModels are problematic in Odoo v9, since they
        prevent the new-style computed fields from working correctly.
        This decorator edits the original class in-place, so the Odoo model
        is left unchanged. """
    cls.activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        domain=lambda self: [('res_model', '=', self._name)])
    cls.activity_state = fields.Selection([
        ('overdue', 'Overdue'),
        ('today', 'Today'),
        ('planned', 'Planned')], string='State',
        compute='_compute_activity_state',
        help='Status based on activities\n'
        'Overdue: Due date is already passed\n'
        'Today: Activity date is today\nPlanned: Future activities.')
    cls.activity_user_id = fields.Many2one(
        'res.users', 'Responsible',
        related='activity_ids.user_id',
        search='_search_activity_user_id')
    cls.activity_type_id = fields.Many2one(
        'mail.activity.type', 'Next Activity Type',
        related='activity_ids.activity_type_id',
        search='_search_activity_type_id')
    cls.activity_date_deadline = fields.Date(
        'Next Activity Deadline', related='activity_ids.date_deadline',
        readonly=True, store=True)  # store to enable ordering + search
    cls.activity_summary = fields.Char(
        'Next Activity Summary', related='activity_ids.summary',
        search='_search_activity_summary')
    cls.nbr_activities = fields.Integer(compute='_compute_nbr_activities')

    @api.depends('activity_ids')
    def _compute_nbr_activities(self):
        for record in self:
            record.nbr_activities = len(record.activity_ids)
    cls._compute_nbr_activities = _compute_nbr_activities

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
    cls._compute_activity_state = _compute_activity_state

    @api.model
    def _search_activity_user_id(self, operator, operand):
        return [('activity_ids.user_id', operator, operand)]
    cls._search_activity_user_id = _search_activity_user_id

    @api.model
    def _search_activity_type_id(self, operator, operand):
        return [('activity_ids.activity_type_id', operator, operand)]
    cls._search_activity_type_id = _search_activity_type_id

    @api.model
    def _search_activity_summary(self, operator, operand):
        return [('activity_ids.summary', operator, operand)]
    cls._search_activity_summary = _search_activity_summary

    original_unlink = cls.unlink

    @api.multi
    def unlink(self):
        """ Override unlink to delete records activities through
        (res_model, res_id). """
        record_ids = self.ids
        result = original_unlink(self)
        self.env['mail.activity'].sudo().search(
            [('res_model', '=', self._name), ('res_id', 'in', record_ids)]
        ).unlink()
        return result
    cls.unlink = unlink

    return cls
