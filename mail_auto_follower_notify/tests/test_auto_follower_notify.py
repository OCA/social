# -*- coding: utf-8 -*-
# Copyright <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase


class TestAutoFollowerNotify(TransactionCase):
    def setUp(self):
        super(TestAutoFollowerNotify, self).setUp()
        self.test_record = self.env['res.partner'].create({
            'name': 'Test Record',
        })
        self.user = self.env['res.users'].create({
            'name': 'Test user',
            'login': 'test_login',
        })

    def test_something(self):
        """Test module functionality."""
        items = self.test_record._fields.items()
        user_id = filter(lambda (n, f): n == 'user_id', items)
        # Set manually a res.users field to track visibility in order to be
        # able to test the module without extra dependencies.
        setattr(user_id[0][1], 'track_visibility', 'always')
        self.test_record.user_id = self.user.id
        self.assertTrue(
            self.test_record.message_follower_ids, "Follower not notified.")
