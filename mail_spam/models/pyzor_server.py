# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PyzorServer(models.Model):
    _name = 'pyzor.server'
    _description = 'Pyzor Servers'

    name = fields.Char(
        compute='_compute_name',
        search='_search_name',
    )
    host = fields.Char(
        required=True,
    )
    port = fields.Integer(
        required=True,
        default=24441,
    )
    blacklist_ratio = fields.Integer(
        help='This amount of blacklists cancels out one whitelist when '
             'determining if a message is marked as SPAM.',
    )
    host_port = fields.Binary(
        compute='_compute_host_port',
    )

    @api.multi
    @api.depends('host_port')
    def _compute_name(self):
        for record in self:
            record.name = '%s:%s' % (record.host, record.port)

    @api.model
    def _search_name(self, operator, value):
        return [('host', operator, value)]

    @api.multi
    @api.depends('host', 'port')
    def _compute_host_port(self):
        for record in self:
            record.host_port = (record.host, record.port)

    @api.multi
    @api.constrains('blacklist_ratio')
    def _check_blacklist_ratio(self):
        if self.filtered(lambda r: r.blacklist_ratio < 0):
            raise ValidationError(_(
                'The blacklist ratio cannot be less than zero.',
            ))

    @api.multi
    def is_message_spam(self, whitelists, blacklists):
        """Return whether the message is SPAM based on policy.

        Args:
            whitelists (int): Amount of whitelists for message.
            blacklists (int): Amount of blacklists for message.

        Returns:
            bool: Whether the message is SPAM or not, based on the server
            policy.
        """
        self.ensure_one()
        # If ratio is zero, any whitelist cancels a black
        if self.blacklist_ratio == 0:
            return blacklists and not whitelists
        # Otherwise, we divide blacklists to obtain weighted number
        blacklists_adjusted = blacklists / self.blacklist_ratio
        return blacklists_adjusted > whitelists
