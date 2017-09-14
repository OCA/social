# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import logging
import mock

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)

try:
    from reverend.thomas import Bayes
except ImportError:
    _logger.info('`reverend` Python library not installed.')


class TestReverendThomas(TransactionCase):

    def setUp(self):
        super(TestReverendThomas, self).setUp()
        self.Model = self.env['reverend.thomas']
        self.spam = [
            'spam', 'buy', 'sell', 'million',
        ]
        self.ham = [
            'ham', 'business', 'odoo', 'laslabs',
        ]
        self.message = self.env['mail.message'].search([], limit=1)

    def _create_reverend(self, database=None, trained=False):
        reverend = self.Model.create({
            'name': 'Tester',
            'database': database,
        })
        if trained:
            self._train_reverend(reverend)
        return reverend

    def _train_reverend(self, reverend):
        """Train the reverend with a known test set."""
        reverend.client.train(self.Model.SPAM, ' '.join(self.spam))
        reverend.client.train(self.Model.HAM, ' '.join(self.ham))

    def test_client(self):
        """It should set the client."""
        self.assertIsInstance(self._create_reverend().client, Bayes)

    @mock.patch('odoo.addons.mail_anti_spam.models.reverend_thomas.Bayes')
    def test_client_loads(self, bayes):
        """It should load the database."""
        reverend = self._create_reverend()
        call_args = bayes().load_handler.call_args
        self.assertTrue(call_args)
        self.assertEqual(
            call_args[0][0].getvalue(),
            reverend.database.decode('base64'),
        )

    def test_create_new_database(self):
        """It should create and save a new DB if necessary."""
        reverend = self._create_reverend()
        self.assertTrue(reverend.database.decode('base64'))

    def test_check_spam(self, reverend=None):
        """It should return a proper spam classification."""
        if reverend is None:
            reverend = self._create_reverend(trained=True)
        self.message.body = 'spam'
        results = reverend.check(self.message)
        expect = {
            self.Model.SPAM: 0.9999,
            self.Model.HAM: 0,
            'ratio': 0,
            reverend.id: {
                self.Model.SPAM: 0.9999,
            }
        }
        self.assertDictEqual(results, expect)

    def test_check_ham(self, reverend=None):
        """It should return a proper ham classification."""
        if reverend is None:
            reverend = self._create_reverend(trained=True)
        self.message.body = 'ham'
        results = reverend.check(self.message)
        expect = {
            self.Model.HAM: 0.9999,
            self.Model.SPAM: 0,
            'ratio': 1,
            reverend.id: {
                self.Model.HAM: 0.9999,
            }
        }
        self.assertDictEqual(results, expect)

    def test_check_fifty_fifty(self, reverend=None):
        """It should return a proper unsure classification."""
        if reverend is None:
            reverend = self._create_reverend(trained=True)
        self.message.body = 'ham spam'
        results = reverend.check(self.message)
        expect = {
            self.Model.HAM: 0.9999,
            self.Model.SPAM: 0.9999,
            'ratio': 1,
            reverend.id: {
                self.Model.HAM: 0.9999,
                self.Model.SPAM: 0.9999,
            }
        }
        self.assertDictEqual(results, expect)

    def test_train_spam(self):
        """It should properly train for spam."""
        reverend = self._create_reverend()
        self.message.body = ' '.join(self.spam)
        reverend.train_spam(self.message)
        self.test_check_spam()

    def test_train_ham(self):
        """It should properly train for ham."""
        reverend = self._create_reverend()
        self.message.body = ' '.join(self.ham)
        reverend.train_ham(self.message)
        self.test_check_ham()
