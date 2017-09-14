# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging

from io import BytesIO
from collections import defaultdict, OrderedDict

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    from reverend.thomas import Bayes
except ImportError:
    _logger.info('`reverend` Python library not installed.')


class ReverendThomas(models.Model):
    """This model acts as a proxy for Reverend Thomas Bayes operations.

    All actual Bayesian classifications happen in this model, and are stored
    to the internal database file in the ``database`` field.
    """

    _name = 'reverend.thomas'
    _description = 'Bayesian Classifications'

    HAM = 'ham'
    SPAM = 'spam'

    name = fields.Char(
        required=True,
    )
    database = fields.Binary(
        attachment=True,
        readonly=True,
    )
    client = fields.Binary(
        compute='_compute_client',
    )

    @api.multi
    @api.depends('database')
    def _compute_client(self):
        """Compute the client, optionally loading the stored database."""
        for record in self.filtered(lambda r: r.database):
            record.client = self._get_client()
            with BytesIO(record.database.decode('base64')) as fp:
                record.client.load_handler(fp)

    @api.model
    def create(self, vals):
        """Add a new database into vals if one isn't provided."""
        record = super(ReverendThomas, self).create(vals)
        if not vals.get('database'):
            client = self._get_client()
            with BytesIO() as fp:
                client.save_handler(fp)
                record.database = fp.getvalue().encode('base64')
        return record

    @api.multi
    def check(self, message):
        """Check the parsed message and return the results.

        If partners is provided, it will use the Pyzor servers that are mapped
        to their company. Otherwise it will use the current user's company.

        Args:
            message (MailMessage): Message singleton to check as SPAM.

        Returns:
            dict: Mapping with keys `spam`, `ham`, and `ratio`.
        """

        message.ensure_one()

        averages = {self.HAM: 0, self.SPAM: 0}
        output = defaultdict(dict)

        for record in self:
            for result in record.client.guess(self._parse_message(message)):
                key, score = result
                averages[key] = averages.get(key, 0) + score
                output[record.id][key] = score

        averages['ratio'] = averages[self.HAM] / (averages[self.SPAM] or 1)

        output.update(averages)
        return output

    @api.multi
    def train_spam(self, messages):
        """Report a message as SPAM.

        Args:
            messages (MailMessage): ``mail.message`` recordset to mark as SPAM.
        """
        self._train(messages, self.SPAM)

    @api.multi
    def train_ham(self, messages):
        """Report a message as SPAM.

        Args:
            messages (MailMessage): ``mail.message`` recordset to mark as HAM.
        """
        self._train(messages, self.HAM)

    @api.multi
    def _train(self, messages, spam_or_ham):
        """Train the Bayesian filter.

        Args:
            messages (MailMessage): ``mail.message`` recordset to train with.
            spam_or_ham (str): Value to train as (either self.SPAM or self.HAM)
        """
        for record in self:
            for message in messages:
                message_string = self._parse_message(message)
                record.client.train(message_string, spam_or_ham)
        self._save_db()

    @staticmethod
    def _get_client():
        """Return a Bayes client."""
        return Bayes()

    @staticmethod
    def _get_message_training_parts(message):
        """Parse a ``mail.message`` object"""
        message.ensure_one()
        author = message.author_id
        from_header = author and author.email or message.email_from
        return OrderedDict([
            ('from', 'FROM: %s' % from_header),
            ('body', message.body),
        ])

    @classmethod
    def _parse_message(cls, message):
        """Parse a ``mail.message`` record into a string for training."""
        return '\n'.join(cls._get_message_training_parts(message))

    @api.multi
    def _save_db(self):
        """Save the trained database."""
        for record in self:
            with BytesIO() as fp:
                record.client.save_handler(fp)
            record.database = fp.getvalue()
