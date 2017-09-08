# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import hashlib
import random
import sys

from odoo import api, fields, models


class PyzorAccount(models.Model):
    _name = 'pyzor.account'
    _description = 'Pyzor Accounts'

    name = fields.Char(
        compute='_compute_name',
    )
    server_id = fields.Many2one(
        string='Server',
        comodel_name='pyzor.server',
    )
    username = fields.Char(
        required=True,
    )
    password = fields.Char(
        compute=lambda s: False,
        inverse='_inverse_password',
    )
    password_hash = fields.Char(
        readonly=True,
    )
    file_line = fields.Char(
        compute='_compute_file_line',
    )

    @api.multi
    @api.depends('server_id.name', 'username')
    def _compute_name(self):
        for record in self:
            record.name = '%s (%s)' % (record.server_id.name, record.username)

    @api.multi
    def _inverse_password(self):
        for record in self:
            record.password_hash = self.get_pass_key(record.password)

    @api.multi
    @api.depends('username',
                 'password_hash',
                 'server_id.host',
                 'server_id.port',
                 )
    def _compute_file_line(self):
        for record in self:
            record.file_line = '%s : %s : %s : %s' % (
                record.server_id.host,
                record.server_id.port,
                record.username,
                record.password_hash,
            )

    @api.model_cr_context
    def get_pass_key(self, password, hash_method=hashlib.sha256):
        """Generate a key to use as Pyzor authentication.

        Args:
            password (str): Plain text password to hash.
            hash_method (callable, optional): Method to use for hashing.

        Returns:
            str: Password key string as required by Pyzor
            ("salt_digest,pass_digest")
        """
        salt = "".join([chr(random.randint(0, 255))
                        for _ in range(hash_method(b"").digest_size)])
        # Compatibility with Python3 (future)
        if sys.version_info >= (3, 0):
            salt = salt.encode("utf8")
        salt_digest = hash_method(salt)
        pass_digest = hash_method(salt_digest.digest())
        pass_digest.update(password.encode("utf8"))
        return '%s,%s' % (salt_digest.hexdigest(), pass_digest.hexdigest())
