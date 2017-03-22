# -*- coding: utf-8 -*-
# Copyright 2017 Simone Orsi <simone.orsi@camptocamp.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp.tests.common import TransactionCase


class PartnerDomainCase(TransactionCase):

    def setUp(self):
        super(PartnerDomainCase, self).setUp()
        self.partner_model = self.env['res.partner']
        self.message_model = self.env['mail.message']
        self.subtype_model = self.env['mail.message.subtype']

        self.partner1 = self.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 1',
                'email': 'partner1@test.foo.com',
            })
        self.partner2 = self.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 2',
                'email': 'partner2@test.foo.com',
            })
        self.partner3 = self.partner_model.with_context(
            tracking_disable=1).create({
                'name': 'Partner 3',
                'email': 'partner3@test.foo.com',
            })
        self.subtype1 = self.subtype_model.create({'name': 'Type 1'})
        self.subtype2 = self.subtype_model.create({'name': 'Type 2'})

    def _assert_found(self, domain, not_found=False, partner=None):
        partner = partner or self.partner1
        if not_found:
            self.assertNotIn(partner, self.partner_model.search(domain))
        else:
            self.assertIn(partner, self.partner_model.search(domain))

    def test_notify_domains_always(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.notify_email = 'always'
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(domain)
        domain = partner._get_notify_by_email_domain(message, digest=1)
        self._assert_found(domain, not_found=1)

    def test_notify_domains_only_recipients(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        self.partner1.notify_email = 'always'
        self.partner2.notify_email = 'always'
        partners = self.partner1 + self.partner2
        # followers
        self.partner3.message_subscribe(self.partner2.ids)
        # partner1 is the only recipient
        message = self.message_model.create({
            'body': 'My Body',
            'res_id': self.partner3.id,
            'model': 'res.partner',
            'partner_ids': [(4, self.partner1.id)]
        })
        domain = partners._get_notify_by_email_domain(message)
        # we find both of them since partner2 is a follower
        self._assert_found(domain)
        self._assert_found(domain, partner=self.partner2)
        # no one here in digest mode
        domain = partners._get_notify_by_email_domain(message, digest=1)
        self._assert_found(domain, not_found=1)
        self._assert_found(domain, not_found=1, partner=self.partner2)

        # include only recipients
        domain = partners.with_context(
            notify_only_recipients=1)._get_notify_by_email_domain(message)
        self._assert_found(domain)
        self._assert_found(domain, partner=self.partner2, not_found=1)

    def test_notify_domains_digest(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.notify_email = 'digest'
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(domain, not_found=1)
        domain = partner._get_notify_by_email_domain(message, digest=1)
        self._assert_found(domain)

    def test_notify_domains_none(self):
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.notify_email = 'none'
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(domain, not_found=1)
        domain = partner._get_notify_by_email_domain(message, digest=1)
        self._assert_found(domain, not_found=1)

    def test_notify_domains_match_type_digest(self):
        # Test message subtype matches partner settings.
        # The partner can have several `partner.notification.conf` records.
        # Each records establish notification rules by type.
        # If you don't have any record in it, you allow all subtypes.
        # Record `typeX` with `enable=True` enables notification for `typeX`.
        # Record `typeX` with `enable=False` disables notification for `typeX`.

        partner = self.partner1
        # enable digest
        partner.notify_email = 'digest'
        message_t1 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype1.id,
        })
        message_t2 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype2.id,
        })
        # enable subtype on partner
        partner._notify_enable_subtype(self.subtype1)
        domain = partner._get_notify_by_email_domain(
            message_t1, digest=True)
        # notification enabled: we find the partner.
        self._assert_found(domain)
        # for subtype2 we don't have any explicit rule: we find the partner
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(domain)
        # enable subtype2: find the partner anyway
        partner._notify_enable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(domain)
        # disable subtype2: we don't find the partner anymore
        partner._notify_disable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(domain, not_found=1)

    def test_notify_domains_match_type_always(self):
        message_t1 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype1.id,
        })
        message_t2 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype2.id,
        })
        # enable always
        partner = self.partner1
        partner.notify_email = 'always'
        # enable subtype on partner
        partner._notify_enable_subtype(self.subtype1)
        domain = partner._get_notify_by_email_domain(message_t1)
        # notification enabled: we find the partner.
        self._assert_found(domain)
        # for subtype2 we don't have any explicit rule: we find the partner
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(domain)
        # enable subtype2: find the partner anyway
        partner._notify_enable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(domain)
        # disable subtype2: we don't find the partner anymore
        partner._notify_disable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(domain, not_found=1)
