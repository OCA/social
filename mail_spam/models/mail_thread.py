# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import email
from email.message import Message

from odoo import api, fields, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        partners = self.env['res.partner'].browse(
            [p[1] for p in custom_values['partner_ids']],
        )
        spam_results = self.env['pyzor'].check(
            msg_dict['email_object'], partners,
        )
        custom_values.update({
            'pyzor_whitelist': spam_results['whitelist'],
            'pyzor_blacklist': spam_results['blacklist'],
            'pyzor_digest': spam_results['digest'],
            '_is_spam': spam_results['is_spam'],
        })
        for key, value in spam_results.items():
            custom_values['pyzor_%s' % key] = value
        return super(MailThread, self).message_new(
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
