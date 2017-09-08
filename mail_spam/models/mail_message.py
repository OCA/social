# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    is_spam = fields.Boolean(
        index=True,
        compute='_compute_is_spam',
        inverse='_inverse_is_spam',
        help='Check this to mark the message as SPAM. Uncheck it to add to '
             'whitelist.',
    )
    _is_spam = fields.Boolean(
        readonly=True,
    )
    pyzor_whitelist = fields.Integer()
    pyzor_blacklist = fields.Integer()
    pyzor_digest = fields.Text()
    pyzor_manual_blacklist = fields.Datetime()
    pyzor_manual_whitelist = fields.Datetime()

    @api.multi
    def _compute_is_spam(self):
        for record in self:
            record.is_spam = record._is_spam

    @api.multi
    def _inverse_is_spam(self):
        for record in self.filtered(lambda r: r.is_spam != r._is_spam):
            vals = {'_is_spam': record.is_spam}
            if record.is_spam:
                if record.pyzor_manual_blacklist:
                    self.env['pyzor'].report(
                        record.pyzor_digest, record.partner_ids,
                    )
                    vals['pyzor_manual_blacklist'] = fields.Datetime.now()
            else:
                if not record.pyzor_manual_whitelist:
                    self.env['pyzor'].whitelist(
                        record.pyzor_digest, record.partner_ids,
                    )
                    vals['pyzor_manual_whitelist'] = fields.Datetime.now()
            record.write(vals)

    @api.multi
    def message_format(self):
        messages_values = super(MailMessage, self).message_format()
        for message_values in messages_values:
            message = self.browse(message_values['id'])
            message_values['is_spam'] = message.is_spam
        return messages_values
