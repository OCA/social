# -*- coding: utf-8 -*-
# Copyright 2017 Specialty Medical Drugstore, LLC.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from openerp.tests.common import TransactionCase


class TestMailChannel(TransactionCase):

    def setUp(self):
        super(TestMailChannel, self).setUp()
        self.operator = self.env.ref(
            'website_livechat_firstname.res_partner_1'
        )
        self.customer_name = 'Billy Joe'
        self.channel_vals = {
            'name': '%s, %s' % (self.customer_name, self.operator.name),
            'public': 'public',
        }
        self.mail_mod = self.env['mail.channel']
        self.test_context = {
            'im_livechat_operator_partner_id': self.operator.id,
        }

    def test_channel_info_operator_pid_full_name(self):
        """ Test get operator name correct when full name """
        channel = self.mail_mod.create(self.channel_vals)
        res = channel.with_context(self.test_context).channel_info()
        self.assertEquals(
            res[0]['operator_pid'],
            (self.operator.id, u'%s' % self.operator.firstname),
        )

    def test_channel_info_operator_pid_last_name_only(self):
        """ Test get operator name correct if only lastname """
        self.operator.firstname = None
        channel = self.mail_mod.create(self.channel_vals)
        res = channel.with_context(self.test_context).channel_info()
        self.assertEquals(
            res[0]['operator_pid'],
            (self.operator.id, u'%s' % self.operator.name),
        )

    def test_channel_info_name(self):
        """ Test operator name shortened correctly in channel name """
        channel = self.mail_mod.create(self.channel_vals)
        res = channel.with_context(self.test_context).channel_info()
        self.assertEquals(
            res[0]['name'],
            '%s, %s' % (self.customer_name, self.operator.firstname),
        )

    def test_channel_info_no_context(self):
        """ Test channel_name same if no context passsed """
        channel = self.mail_mod.create(self.channel_vals)
        res = channel.channel_info()
        self.assertEquals(
            res[0]['name'],
            '%s, %s' % (self.customer_name, self.operator.name),
        )

    def test_channel_info_not_public(self):
        """ Test channel info unchanged if not public channel """
        self.channel_vals['public'] = 'private'
        channel = self.mail_mod.create(self.channel_vals)
        res = channel.with_context(self.test_context).channel_info()
        self.assertEquals(
            res[0]['name'],
            '%s, %s' % (self.customer_name, self.operator.name),
        )
