# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from datetime import datetime

from odoo import api, fields, models
from odoo.addons.bus.models.bus_presence import AWAY_TIMER, DISCONNECTION_TIMER

from ..status_constants import ONLINE, AWAY, OFFLINE


class BusPresence(models.Model):

    _inherit = 'bus.presence'

    status_realtime = fields.Selection(
        selection=[
            (ONLINE, 'Online'),
            (AWAY, 'Away'),
            (OFFLINE, 'Offline')
        ],
        string='Realtime IM Status',
        compute='_compute_status_realtime',
        help='Status that is affected by disconnection '
             'and away timers. Used to override the bus.presence '
             'status field in _get_partners_statuses or '
             '_get_users_statuses if the timers have been reached. '
             'If wanting to change the user status, write '
             'directly to the status field.',
    )
    partner_id = fields.Many2one(
        string='Partner',
        related='user_id.partner_id',
        comodel_name='res.partner',
    )

    @api.multi
    def _get_partners_statuses(self):
        self._status_check_disconnection_and_away_timers()
        return {rec.partner_id.id: rec.status for rec in self}

    @api.multi
    def _get_users_statuses(self):
        self._status_check_disconnection_and_away_timers()
        return {rec.user_id.id: rec.status for rec in self}

    @api.multi
    def _status_check_disconnection_and_away_timers(self):
        """ Overrides user-defined status if timers reached """
        for record in self:

            status_realtime = record.status_realtime
            status_stored = record.status

            conditions = (
                status_realtime == OFFLINE,
                status_realtime == AWAY and status_stored == ONLINE,
            )

            if any(conditions):
                record.status = status_realtime

    @api.multi
    def _compute_status_realtime(self):

        now_dt = datetime.now()

        for record in self:

            last_poll = fields.Datetime.from_string(
                record.last_poll
            )
            last_presence = fields.Datetime.from_string(
                record.last_presence
            )

            last_poll_s = (now_dt - last_poll).total_seconds()
            last_presence_s = (now_dt - last_presence).total_seconds()

            if last_poll_s > DISCONNECTION_TIMER:
                record.status_realtime = OFFLINE

            elif last_presence_s > AWAY_TIMER:
                record.status_realtime = AWAY

            else:
                record.status_realtime = ONLINE
