# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from mock import patch

from .bus_setup import BusSetup
from ..status_constants import ONLINE

AWAY_TIMER = 'odoo.addons.bus_presence_override.models.' \
             'bus_presence.AWAY_TIMER'

DISCONNECTION_TIMER = 'odoo.addons.bus_presence_override.models.' \
                      'bus_presence.DISCONNECTION_TIMER'


class TestResPartner(BusSetup):

    @patch(AWAY_TIMER, 10000000)
    @patch(DISCONNECTION_TIMER, 10000000)
    def test_compute_im_status_online(self):
        """ It should be computed to online """
        self.pres_admin.status = ONLINE
        self.assertEquals(
            self.p_admin.im_status,
            ONLINE,
        )
