# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp.tests.common import TransactionCase


class SubtypesCase(TransactionCase):

    def setUp(self):
        super(SubtypesCase, self).setUp()
        self.partner_model = self.env['res.partner']
        self.message_model = self.env['mail.message']
        self.subtype_model = self.env['mail.message.subtype']

        self.partner1 = self.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 1!',
                'email': 'partner1@test.foo.com',
            })
        self.partner2 = self.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 2!',
                'email': 'partner2@test.foo.com',
            })
        self.subtype1 = self.subtype_model.create({'name': 'Type 1'})
        self.subtype2 = self.subtype_model.create({'name': 'Type 2'})

    def _test_subtypes_rel(self):
        # setup:
        # t1, t2 enabled
        # t3 disabled
        # t4 no conf
        self.subtype3 = self.subtype_model.create({'name': 'Type 3'})
        self.subtype4 = self.subtype_model.create({'name': 'Type 4'})
        # enable t1 t2
        self.partner1._notify_enable_subtype(self.subtype1)
        self.partner1._notify_enable_subtype(self.subtype2)
        # disable t3
        self.partner1._notify_disable_subtype(self.subtype3)

    def test_partner_computed_subtype(self):
        self._test_subtypes_rel()
        # check computed fields
        self.assertIn(
            self.subtype1, self.partner1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype1, self.partner1.disabled_notify_subtype_ids)
        self.assertIn(
            self.subtype2, self.partner1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype2, self.partner1.disabled_notify_subtype_ids)
        self.assertIn(
            self.subtype3, self.partner1.disabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype3, self.partner1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype4,
            self.partner1.enabled_notify_subtype_ids)
        self.assertNotIn(
            self.subtype4,
            self.partner1.disabled_notify_subtype_ids)

    def test_partner_find_by_subtype_incl(self):
        self._test_subtypes_rel()
        domain = [(
            'enabled_notify_subtype_ids',
            'in', (self.subtype1.id, self.subtype2.id),
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'disabled_notify_subtype_ids', 'in', self.subtype3.id,
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'enabled_notify_subtype_ids', 'in', (self.subtype3.id, ),
        )]
        self.assertNotIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'enabled_notify_subtype_ids', 'in', (self.subtype4.id, ),
        )]
        self.assertNotIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'disabled_notify_subtype_ids', 'in', (self.subtype4.id, ),
        )]
        self.assertNotIn(
            self.partner1,
            self.partner_model.search(domain)
        )

    def test_partner_find_by_subtype_escl(self):
        self._test_subtypes_rel()
        domain = [(
            'enabled_notify_subtype_ids',
            'not in', (self.subtype4.id, ),
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'disabled_notify_subtype_ids',
            'not in', (self.subtype4.id, ),
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'enabled_notify_subtype_ids',
            'not in', (self.subtype3.id, ),
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
        domain = [(
            'disabled_notify_subtype_ids',
            'not in', (self.subtype1.id, self.subtype2.id),
        )]
        self.assertIn(
            self.partner1,
            self.partner_model.search(domain)
        )
