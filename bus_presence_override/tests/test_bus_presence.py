# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from mock import patch

from .bus_setup import BusSetup
from ..status_constants import ONLINE, AWAY, OFFLINE

AWAY_TIMER = 'odoo.addons.bus_presence_override.models.' \
             'bus_presence.AWAY_TIMER'

DISCONNECTION_TIMER = 'odoo.addons.bus_presence_override.models.' \
                      'bus_presence.DISCONNECTION_TIMER'


class TestBusPresence(BusSetup):

    @patch(AWAY_TIMER, 10000000)
    @patch(DISCONNECTION_TIMER, 10000000)
    def test_compute_status_realtime_online(self):
        """ It should be computed to online """
        self.assertEquals(
            self.pres_admin.status_realtime,
            ONLINE,
        )

    @patch(AWAY_TIMER, 10000000)
    @patch(DISCONNECTION_TIMER, 0)
    def test_compute_status_realtime_offline(self):
        """ It should be computed to offline """
        self.assertEquals(
            self.pres_admin.status_realtime,
            OFFLINE,
        )

    @patch(AWAY_TIMER, 0)
    @patch(DISCONNECTION_TIMER, 10000000)
    def test_compute_status_realtime_away(self):
        """ It should be computed to away """
        self.assertEquals(
            self.pres_admin.status_realtime,
            AWAY,
        )

    @patch(AWAY_TIMER, 0)
    @patch(DISCONNECTION_TIMER, 0)
    def test_compute_status_realtime_both(self):
        """ It should be computed to offline even though away as well """
        self.assertEquals(
            self.pres_admin.status_realtime,
            OFFLINE,
        )

    @patch(AWAY_TIMER, 0)
    @patch(DISCONNECTION_TIMER, 0)
    def test_status_check_timers_offline(self):
        """ It should be changed to offline from online """
        self.pres_admin.status = ONLINE
        self.assertEquals(
            self.pres_admin.status,
            ONLINE,
        )
        self.pres_admin._status_check_disconnection_and_away_timers()
        self.assertEquals(
            self.pres_admin.status,
            OFFLINE,
        )

    @patch(AWAY_TIMER, 0)
    @patch(DISCONNECTION_TIMER, 10000000)
    def test_status_check_timers_away(self):
        """ It should be changed to away from online """
        self.pres_admin.status = ONLINE
        self.assertEquals(
            self.pres_admin.status,
            ONLINE,
        )
        self.pres_admin._status_check_disconnection_and_away_timers()
        self.assertEquals(
            self.pres_admin.status,
            AWAY,
        )

    @patch(AWAY_TIMER, 0)
    @patch(DISCONNECTION_TIMER, 10000000)
    def test_status_check_timers_unchanged(self):
        """ It should remain at offline even if status_realtime away """
        self.pres_admin.status = OFFLINE
        self.assertEquals(
            self.pres_admin.status,
            OFFLINE,
        )
        self.pres_admin._status_check_disconnection_and_away_timers()
        self.assertEquals(
            self.pres_admin.status,
            OFFLINE,
        )

    def test_get_partners_im_statuses(self):
        """ It should include demo and admin partner statuses """
        recs = self.env['bus.presence'].search([(
            'partner_id', 'in', [self.p_admin.id, self.p_demo.id])]
        )
        statuses = recs._get_partners_statuses()
        self.assertIn(
            self.p_admin.id,
            statuses,
        )

    def test_get_users_im_statuses(self):
        """ It should include demo and admin user statuses """
        recs = self.env['bus.presence'].search([(
            'user_id', 'in', [self.u_admin.id, self.u_demo.id])]
        )
        statuses = recs._get_users_statuses()
        self.assertIn(
            self.u_admin.id,
            statuses,
        )
