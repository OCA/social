# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from contextlib import contextmanager
from mock import MagicMock

from odoo.tests.common import TransactionCase


class TestMailMessage(TransactionCase):

    def setUp(self):
        super(TestMailMessage, self).setUp()
        self.Model = self.env['mail.message']
        self.sender = self.env.user.partner_id
        self.recipient = self.env.ref('base.user_demo').partner_id
        self.body = 'Test message'
        self.reverends = self.env['reverend.thomas'].search([])

    def _create_message(self):
        return self.Model.create({
            'subject': 'Message test',
            'author_id': self.sender.id,
            'email_from': self.sender.email,
            'message_type': 'comment',
            'model': 'res.partner',
            'res_id': self.recipient.id,
            'partner_ids': [(4, self.recipient.id)],
            'body': self.body,
        })

    @contextmanager
    def _mock_trainer(self, spam_or_ham):
        trainer = MagicMock()
        method = 'train_%s' % spam_or_ham
        self.env['reverend.thomas']._patch_method(method, trainer)
        try:
            yield trainer
        finally:
            self.env['reverend.thomas']._revert_method(method)

    def test_compute_is_spam(self):
        """It should mirror the ``_is_spam`` attribute."""
        message = self._create_message()
        message._is_spam = True
        self.assertTrue(message.is_spam)
        message._is_spam = False
        self.assertFalse(message.is_spam)

    def test_inverse_is_spam_spam(self):
        """It should train for spam when marked as spam."""
        with self._mock_trainer('spam') as trainer:
            message = self._create_message()
            message._is_spam = False
            message.is_spam = True
            trainer.assert_called_once_with(message)

    def test_inverse_is_spam_ham(self):
        """It should train for ham when marked as ham."""
        with self._mock_trainer('ham') as trainer:
            message = self._create_message()
            message._is_spam = True
            message.is_spam = False
            trainer.assert_called_once_with(message)

    def test_inverse_is_spam_no_change(self):
        """It should not attempt to train when there is not a change."""
        with self._mock_trainer('ham') as trainer:
            message = self._create_message()
            message._is_spam = False
            message.is_spam = False
            trainer.assert_not_called()

    def test_search_is_spam(self):
        """It should be able to search on ``is_spam``."""
        message = self._create_message()
        messages = self.Model.search([('is_spam', '=', message._is_spam)])
        self.assertIn(message, messages)

    def test_create_injects_spam_score_ham(self):
        """It should add the SPAM values into the record on create (HAM)."""
        message = self._create_message()
        expect = {
            'is_spam': False,
            'spam_ratio': 1,
            'spam_score': 0,
            'ham_score': 0.9999,
        }
        result = {k: message[k] for k in expect.keys()}
        self.assertDictEqual(result, expect)

    def test_create_injects_spam_score_spam(self):
        """It should add the SPAM values into the record on create (SPAM)."""
        message = self._create_message()
        self.reverends.train_spam(message)
        message = self._create_message()
        expect = {
            'is_spam': True,
            'spam_ratio': 0,
            'spam_score': 0.9999,
            'ham_score': 0,
        }
        result = {k: message[k] for k in expect.keys()}
        self.assertDictEqual(result, expect)
