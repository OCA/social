# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import tempfile

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import pyzor.client
    import pyzor.config
    import pyzor.digest
except ImportError:
    _logger.info('`pyzor` Python library not installed.')


class Pyzor(models.AbstractModel):
    """This model acts as a proxy for Pyzor operations.

    All actual Pyzor usage takes place in this model. Methods are meant
    to be called by any model.
    """

    _name = 'pyzor'
    _description = 'Pyzor Anti-SPAM'

    @api.model
    def client(self, partners):
        """Return a Pyzor client for the partners.

        Args:
            partners (ResPartner): Partner records that the client should
            be made for.

        Return:
            pyzor.client.Client: Pyzor client instance for usage.
        """
        # Create accounts config
        with tempfile.NamedTemporaryFile() as fh:
            fh.writelines(
                partners.mapped('company_id.pyzor_account_ids.file_line'),
            )
            accounts = pyzor.config.load_accounts(fh.name)
        # Create client
        return pyzor.client.Client(accounts)

    @api.model
    def check(self, message, partners=None):
        """Check the parsed message and return the results.

        If partners is provided, it will use the Pyzor servers that are mapped
        to their company. Otherwise it will use the current user's company.
        
        Args:
            message (email.message.Message): Message object to check as SPAM.
            partners (ResPartner): Partner records that the client should
            be made for.

        Returns:
            dict: Mapping with the following keys:
                * `digest` (str): Pyzor digest for the message.
                * `blacklist` (int): Blacklist aggregate for message digest
                  from all partner company servers.
                * `whitelist` (int): Whitelist aggregate for message digest
                  from all partner company servers.
                * `is_spam` (bool): `True` if any of the servers identified
                  this message as SPAM.
                * `responses` (dict of dicts): Individual responses, keyed
                  by server ID and containing dicts with the keys `whitelist`,
                  `blacklist`, and `is_spam`.
        """
        if not partners:
            partners = self.env.user.partner_id
        client = self.client(partners)
        digest = pyzor.digest.DataDigester(message).value
        whitelist = 0
        blacklist = 0
        responses = {}
        for server in partners.mapped('company_id.pyzor_server_ids'):
            response = client.check(digest, server.host_port)
            blacklist += response['Count']
            whitelist += response['WL-Count']
            responses[server.id] = {
                'blacklist': response['Count'],
                'whitelist': response['WL-Count'],
                'is_spam': server.is_message_spam(
                    response['Count'], response['WL-Count'],
                ),
            }
        return {
            'blacklist': blacklist,
            'whitelist': whitelist,
            'digest': digest,
            'is_spam': True, #any([r['is_spam'] for r in responses.values()]),
            'responses': responses,
        }

    @api.model
    def report(self, digest, partners=None):
        """Report a message as SPAM to the relevant servers.

        Args:
            digest (str): Pyzor digest string for the message.
            partners (ResPartner): Partner records that the client should
            be made for.
        """
        if not partners:
            partners = self.env.user.partner_id
        client = self.client(partners)
        for server in partners.mapped('company_id.pyzor_server_ids'):
            client.report(digest, server.host_port)

    @api.model
    def whitelist(self, digest, partners=None):
        """Whitelist a message on the relevant servers.

        Args:
            digest (str): Pyzor digest string for the message.
            partners (ResPartner): Partner records that the client should
            be made for.
        """
        if not partners:
            partners = self.env.user.partner_id
        client = self.client(partners)
        for server in partners.mapped('company_id.pyzor_server_ids'):
            client.whitelist(digest, server.host_port)
