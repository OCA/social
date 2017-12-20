# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class SpamAbstract(models.AbstractModel):
    """This model defines the SPAM Adapter interface.
    """

    _name = 'spam.abstract'
    _description = 'SPAM Filter Interface'

    HAM = 'ham'
    SPAM = 'spam'

    name = fields.Char(
        required=True,
    )
    client = fields.Binary(
        compute='_compute_client',
    )

    @api.multi
    def _compute_client(self):
        """Compute a usable client."""
        pass

    @api.multi
    def check(self, message):
        """Check the parsed message and return the results.

        Args:
            message (MailMessage): Message singleton to check as SPAM.

        Returns:
            dict: Mapping with keys `spam`, `ham`, and `ratio`. It also
            includes the individual results keyed by the adapter ID.
        """

        message.ensure_one()

        averages = {self.HAM: 0, self.SPAM: 0}
        output = defaultdict(dict)

        for record in self:
            for result in record.client.guess(self._parse_message(message)):
                _logger.debug('Got result %s', result)
                key, score = result
                averages[key] += score
                output[record.id][key] = score

        output_length = len(output)
        if output_length:
            for key, val in averages.items():
                averages[key] = val / len(output)

        if averages[self.SPAM]:
            averages['ratio'] = averages[self.HAM] / averages[self.SPAM]
        else:
            averages['ratio'] = 1

        _logger.debug('Averages: %s', averages)

        output.update(averages)
        return dict(output)

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
        messages.write({'reverend_trained': spam_or_ham})
        self._save_db()

    @classmethod
    def _get_client(cls):
        """Return a Bayes client."""
        return Bayes()

    @classmethod
    def _get_message_training_parts(cls, message):
        """Parse a ``mail.message`` object"""
        message.ensure_one()
        author = message.author_id
        from_header = author and author.email or message.email_from
        return OrderedDict([
            ('from', 'FROM: %s' % from_header),
            ('body', str(message.body)),
        ])

    @classmethod
    def _parse_message(cls, message):
        """Parse a ``mail.message`` record into a string for training."""
        return '\n'.join(cls._get_message_training_parts(message).values())

    @api.multi
    def _save_db(self):
        """Save the trained database."""
        for record in self:
            with BytesIO() as fp:
                record.client.save_handler(fp)
                record.database = fp.getvalue().encode('base64')
