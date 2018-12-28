# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class EmailTemplatePlaceholder(models.Model):

    _name = 'email.template.placeholder'
    _description = 'Email Template Placeholder'

    name = fields.Char(string='Placeholder', required=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', required=True)
    placeholder = fields.Char(
        string='Placeholder value',
        required=True, default='${object.}')
    active = fields.Boolean(default=True)
