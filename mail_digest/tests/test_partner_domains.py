# Copyright 2017-2018 Camptocamp - Simone Orsi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import SavepointCase


class PartnerDomainCase(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(PartnerDomainCase, cls).setUpClass()

        cls.partner_model = cls.env['res.partner']
        cls.message_model = cls.env['mail.message']
        cls.subtype_model = cls.env['mail.message.subtype']

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
        cls.user3 = user_model.create({
            'name': 'User 3',
            'login': 'testuser3',
            'email': 'testuser3@email.com',
        })
        cls.partner1 = cls.user1.partner_id
        cls.partner2 = cls.user2.partner_id
        cls.partner3 = cls.user3.partner_id

        cls.subtype1 = cls.subtype_model.create({'name': 'Type 1'})
        cls.subtype2 = cls.subtype_model.create({'name': 'Type 2'})

    def _assert_found(self, partner, domain, not_found=False):
        if not_found:
            self.assertNotIn(partner, self.partner_model.search(domain))
        else:
            self.assertIn(partner, self.partner_model.search(domain))

    def test_notify_domains_always(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.real_user_id.notification_type = 'email'
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(partner, domain)
        domain = partner._get_notify_by_email_domain(message, digest=True)
        self._assert_found(partner, domain, not_found=True)

    def test_notify_domains_only_recipients(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        self.partner1.real_user_id.notification_type = 'email'
        self.partner2.real_user_id.notification_type = 'email'
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
        self._assert_found(self.partner1, domain)
        self._assert_found(self.partner2, domain)
        # no one here in digest mode
        domain = partners._get_notify_by_email_domain(message, digest=True)
        self._assert_found(self.partner1, domain, not_found=True)
        self._assert_found(self.partner2, domain, not_found=True)

        # include only recipients
        domain = partners.with_context(
            notify_only_recipients=1)._get_notify_by_email_domain(message)
        self._assert_found(self.partner1, domain)
        self._assert_found(self.partner2, domain, not_found=True)

    def test_notify_domains_digest(self):
        # we don't set recipients
        # because we call `_get_notify_by_email_domain` directly
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.real_user_id.write({
            'notification_type': 'email',
            'digest_mode': True,
        })
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(partner, domain, not_found=True)
        domain = partner._get_notify_by_email_domain(message, digest=True)
        self._assert_found(partner, domain)

    def test_notify_domains_none(self):
        message = self.message_model.create({'body': 'My Body', })
        partner = self.partner1
        partner.real_user_id.write({
            'notification_type': 'inbox',
        })
        domain = partner._get_notify_by_email_domain(message)
        self._assert_found(partner, domain, not_found=True)
        domain = partner._get_notify_by_email_domain(message, digest=True)
        self._assert_found(partner, domain, not_found=True)

    def test_notify_domains_match_type_digest(self):
        # Test message subtype matches partner settings.
        # The partner can have several `user.notification.conf` records.
        # Each records establish notification rules by type.
        # If you don't have any record in it, you allow all subtypes.
        # Record `typeX` with `enable=True` enables notification for `typeX`.
        # Record `typeX` with `enable=False` disables notification for `typeX`.

        partner = self.partner1
        # enable digest
        partner.real_user_id.write({
            'notification_type': 'email',
            'digest_mode': True,
        })
        message_t1 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype1.id,
        })
        message_t2 = self.message_model.create({
            'body': 'My Body',
            'subtype_id': self.subtype2.id,
        })
        # enable subtype on partner
        partner.real_user_id._notify_enable_subtype(self.subtype1)
        domain = partner._get_notify_by_email_domain(
            message_t1, digest=True)
        # notification enabled: we find the partner.
        self._assert_found(partner, domain)
        # for subtype2 we don't have any explicit rule: we find the partner
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(partner, domain)
        # enable subtype2: find the partner anyway
        partner.real_user_id._notify_enable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(partner, domain)
        # disable subtype2: we don't find the partner anymore
        partner.real_user_id._notify_disable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(
            message_t2, digest=True)
        self._assert_found(partner, domain, not_found=True)

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
        partner.real_user_id.notification_type = 'email'
        # enable subtype on partner
        partner.real_user_id._notify_enable_subtype(self.subtype1)
        domain = partner._get_notify_by_email_domain(message_t1)
        # notification enabled: we find the partner.
        self._assert_found(partner, domain)
        # for subtype2 we don't have any explicit rule: we find the partner
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(partner, domain)
        # enable subtype2: find the partner anyway
        partner.real_user_id._notify_enable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(partner, domain)
        # disable subtype2: we don't find the partner anymore
        partner.real_user_id._notify_disable_subtype(self.subtype2)
        domain = partner._get_notify_by_email_domain(message_t2)
        self._assert_found(partner, domain, not_found=True)
