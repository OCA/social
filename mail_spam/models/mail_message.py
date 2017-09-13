# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class MailMessage(models.Model):

    _inherit = 'mail.message'

    is_spam = fields.Boolean(
        compute='_compute_is_spam',
        inverse='_inverse_is_spam',
        search='_search_is_spam',
        help='Check this to mark the message as SPAM. Uncheck it to add to '
             'train_ham.',
    )
    _is_spam = fields.Boolean(
        readonly=True,
        index=True,
    )
    spam_ratio = fields.Float(
        help='Likelihood that this message is spam. >1 is ham.',
    )
    spam_score = fields.Float()
    ham_score = fields.Float()

    @api.multi
    def _compute_is_spam(self):
        for record in self:
            record.is_spam = record._is_spam

    @api.multi
    def _inverse_is_spam(self):
        for record in self.filtered(lambda r: r.is_spam != r._is_spam):

            reverends = record._get_all_reverends()

            if record.is_spam:
                reverends.train_spam(record)
            else:
                reverends.train_ham(record)

            record._is_spam = record.is_spam

    @api.model
    def _search_is_spam(self, operator, value):
        return [('_is_spam', operator, value)]

    @api.model
    def create(self, vals):
        """Check the message for SPAM before creation."""
        memory_record = self.new(vals)
        reverends = memory_record._get_all_reverends()
        spam_values = reverends.check(memory_record)
        vals.update({
            '_is_spam': spam_values['ratio'] > 1,
            'spam_ratio': spam_values['ratio'],
            'spam_score': spam_values['spam'],
            'ham_score': spam_values['ham'],
        })
        return super(MailMessage, self).create(vals)

    @api.multi
    def message_format(self):
        messages_values = super(MailMessage, self).message_format()
        for message_values in messages_values:
            message = self.browse(message_values['id'])
            message_values['is_spam'] = message.is_spam
        return messages_values

    @api.multi
    def _get_all_reverends(self):
        """Return all Reverends associated with the singleton Message."""
        self.ensure_one()
        partners = self.partner_ids
        if self.author_id:
            partners |= self.author_id
        return partners.mapped('company_id.reverend_thomas_ids')
