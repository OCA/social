# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from mock import patch

from odoo.tests.common import TransactionCase

from ..status_constants import ONLINE, AWAY, OFFLINE


GET_PRESENCE = 'odoo.addons.bus_presence_override.models.res_partner.' \
               'ResPartner._get_partners_presence'


class TestResPartner(TransactionCase):

    def setUp(self):
        super(TestResPartner, self).setUp()
        self.admin = self.env.ref(
            'base.partner_root',
        )

    @patch(GET_PRESENCE)
    def test_compute_im_status_online(self, get_presence):
        """ im_status_custom and im_status should both be online """
        get_presence.return_value = {self.admin.id: ONLINE}
        self.admin.im_status_custom = ONLINE
        self.assertEquals(
            ONLINE,
            self.admin.im_status,
        )
        self.assertEquals(
            ONLINE,
            self.admin.im_status_custom,
        )

    @patch(GET_PRESENCE)
    def test_compute_im_status_custom_away_override(self, get_presence):
        """ im_status_custom away should override im_status """
        get_presence.return_value = {self.admin.id: ONLINE}
        self.admin.im_status_custom = AWAY
        self.assertEquals(
            AWAY,
            self.admin.im_status,
        )
        self.assertEquals(
            AWAY,
            self.admin.im_status_custom,
        )

    @patch(GET_PRESENCE)
    def test_compute_im_status_custom_offline_override(self, get_presence):
        """ im_status_custom offline should override im_status """
        get_presence.return_value = {self.admin.id: ONLINE}
        self.admin.im_status_custom = OFFLINE
        self.assertEquals(
            OFFLINE,
            self.admin.im_status,
        )
        self.assertEquals(
            OFFLINE,
            self.admin.im_status_custom,
        )

    @patch(GET_PRESENCE)
    def test_compute_im_status_away_override(self, get_presence):
        """ im_status away should override im_status_custom """
        get_presence.return_value = {self.admin.id: AWAY}
        self.admin.im_status_custom = ONLINE
        self.assertEquals(
            AWAY,
            self.admin.im_status,
        )
        self.assertEquals(
            AWAY,
            self.admin.im_status_custom,
        )

    @patch(GET_PRESENCE)
    def test_compute_im_status_offline_override(self, get_presence):
        """ im_status offline should override im_status_custom """
        get_presence.return_value = {self.admin.id: OFFLINE}
        self.admin.im_status_custom = ONLINE
        self.assertEquals(
            OFFLINE,
            self.admin.im_status,
        )
        self.assertEquals(
            OFFLINE,
            self.admin.im_status_custom,
        )
