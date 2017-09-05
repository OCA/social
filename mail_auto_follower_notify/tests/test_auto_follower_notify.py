# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase, at_install, post_install


class TestAutoFollowerNotify(TransactionCase):
    def setUp(self):
        super(TestAutoFollowerNotify, self).setUp()
        self.test_record = self.env['res.partner'].create({
            'name': 'Test Record',
        })
        self.user = self.env['res.users'].create({
             'name': 'Test user',
             'login': 'test_login',
             'password': 'demo',
             'email': 'test@yourcompany.com',
            })

    @at_install(False)
    @post_install(True)
    def test_something(self):
        """Test module functionality. The test must be run after the
        installation to ensure that the patch done in
        ``base_patch_models_mixin`` is applied."""
        # Set manually a res.users field to track visibility in order to be
        # able to test the module without extra dependencies.
        items = self.test_record._fields.items()
        user_id = filter(lambda (n, f): n == 'user_id', items)
        setattr(user_id[0][1], 'track_visibility', 'always')
        # Update the field with a user:
        self.test_record.user_id = self.user.id
        self.assertTrue(
            self.test_record.message_follower_ids, "Follower not notified.")
