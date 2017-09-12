# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import email
from email.message import Message

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

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        partners = self._get_partners_from_tuple(custom_values['partner_ids'])
        spam_values = self._message_spam_values(msg_dict, partners)
        custom_values.update(spam_values)
        return super(MailThread, self).message_new(
            msg_dict, custom_values,
        )

    @api.multi
    def message_update(self, msg_dict, update_values=None):
        if update_values.get('partner_ids'):
            existing_partners = self._get_partners_from_tuple(
                update_values['partner_ids'],
            )
        else:
            existing_partners = self.env['res.partner'].browse()
        for record in self:
            partners = record.partner_ids | existing_partners
            spam_values = self._message_spam_values(msg_dict, partners)
        return super(MailThread, self).message_update(
            msg_dict, custom_values,
        )

    @api.model
    def message_parse(self, message, save_original=False):
        """Add the email message object into the return."""
        message_dict = super(MailThread, self).message_parse(
            message, save_original,
        )
        if not isinstance(message, Message):
            if isinstance(message, unicode):
                # Warning: message_from_string doesn't always work correctly on unicode,
                # we must use utf-8 strings here :-(
                message = message.encode('utf-8')
            message = email.message_from_string(message)
        message_dict['email_object'] = message
        return message_dict

    @api.model
    def _message_spam_values(self, msg_dict, partners=None):
        """Return the SPAM values for the message."""
        values = {}
        spam_results = self.env['pyzor'].check(
            msg_dict['email_object'], partners,
        )
        values.update({
            'pyzor_whitelist': spam_results['whitelist'],
            'pyzor_blacklist': spam_results['blacklist'],
            'pyzor_digest': spam_results['digest'],
            '_is_spam': spam_results['is_spam'],
        })
        return values

    @api.model
    def _get_partners_from_tuple(self, partner_iter):
        """Return the partners that are in the ORM tuple ([4, x], [4, y]).

        Args:
            partner_tuple (iter of iter): Partners that are being added via
            the "4" ORM method. E.g. `[(4, 1), (4, 2)]` to add partner IDs
            `1` and `2`.

        Returns:
            ResPartner: Partners that are being added.
        """
        return self.env['res.partner'].browse([p[1] for p in partner_tuple if p[1]])

