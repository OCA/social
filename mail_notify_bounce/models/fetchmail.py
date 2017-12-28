# -*- coding: utf-8 -*-
# Copyright 2017 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'
    bounce_notify_partner_ids = fields.Many2many(
        'res.partner', string='Notify bounce emails to')
