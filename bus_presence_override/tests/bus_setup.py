# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo.tests.common import TransactionCase


class BusSetup(TransactionCase):

    def setUp(self):
        super(BusSetup, self).setUp()
        self.u_admin = self.env.ref('base.user_root')
        self.p_admin = self.u_admin.partner_id

        self.u_demo = self.env.ref('base.user_demo')
        self.p_demo = self.u_demo.partner_id

        self.pres_admin = self._get_bus_presence(self.u_admin)
        self.pres_demo = self._get_bus_presence(self.u_demo)

        # AWAY_TIMER = 55 seconds
        # DISCONNECTION_TIMER = 1800 seconds (30 minutes)

    def _get_bus_presence(self, user):
        pres = self.env['bus.presence'].search([('user_id', '=', user.id)])
        if not pres:
            pres = self.env['bus.presence'].create({'user_id': user.id})
        return pres
