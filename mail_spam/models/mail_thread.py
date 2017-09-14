# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    is_spam = fields.Boolean(
        compute='_compute_is_spam',
        store=True,
        index=True,
        help='A thread is designated as SPAM if its first message is SPAM.',
    )

    @api.multi
    @api.depends('message_ids.is_spam')
    def _compute_is_spam(self):
        for record in self:
            messages = record.message_ids
            record.is_spam = messages and messages[-1].is_spam
