# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import SavepointCase


class SubtypesCase(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(SubtypesCase, cls).setUpClass()

        user_model = cls.env['res.users'].with_context(
            no_reset_password=True, tracking_disable=True)
        cls.user1 = user_model.create({
            'name': 'User 1',
            'login': 'testuser1',
            'email': 'testuser1@email.com',
        })
        cls.user2 = user_model.create({
            'name': 'User 2',
            'login': 'testuser2',
            'email': 'testuser2@email.com',
        })
        subtype_model = cls.env['mail.message.subtype']
        cls.subtype1 = subtype_model.create({'name': 'Type 1'})
        cls.subtype2 = subtype_model.create({'name': 'Type 2'})
        cls.subtype3 = subtype_model.create({'name': 'Type 3'})
        cls.subtype4 = subtype_model.create({'name': 'Type 4'})

    def _test_subtypes_rel(self):
        # setup:
        # t1, t2 enabled
        # t3 disabled
        # t4 no conf
        # enable t1 t2
        self.user1._notify_enable_subtype(self.subtype1)
        self.user1._notify_enable_subtype(self.subtype2)
        # disable t3
        self.user1._notify_disable_subtype(self.subtype3)

    def test_user_computed_subtype(self):
        self._test_subtypes_rel()
        # check computed fields
        self.assertIn(
            self.subtype1, self.user1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype1, self.user1.disabled_notify_subtype_ids)
        self.assertIn(
            self.subtype2, self.user1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype2, self.user1.disabled_notify_subtype_ids)
        self.assertIn(
            self.subtype3, self.user1.disabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype3, self.user1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype4,
            self.user1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype4,
            self.user1.disabled_notify_subtype_ids)

    def test_find_user_by_subtype_incl(self):
        self._test_subtypes_rel()
        domain = [(
            'enabled_notify_subtype_ids',
            'in', (self.subtype1.id, self.subtype2.id),
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'disabled_notify_subtype_ids', 'in', self.subtype3.id,
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'enabled_notify_subtype_ids', 'in', (self.subtype3.id, ),
        )]
        self.assertNotIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'enabled_notify_subtype_ids', 'in', (self.subtype4.id, ),
        )]
        self.assertNotIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'disabled_notify_subtype_ids', 'in', (self.subtype4.id, ),
        )]
        self.assertNotIn(self.user1, self.env['res.users'].search(domain))

    def test_find_user_by_subtype_escl(self):
        self._test_subtypes_rel()
        domain = [(
            'enabled_notify_subtype_ids',
            'not in', (self.subtype4.id, ),
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'disabled_notify_subtype_ids',
            'not in', (self.subtype4.id, ),
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'enabled_notify_subtype_ids',
            'not in', (self.subtype3.id, ),
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
        domain = [(
            'disabled_notify_subtype_ids',
            'not in', (self.subtype1.id, self.subtype2.id),
        )]
        self.assertIn(self.user1, self.env['res.users'].search(domain))
