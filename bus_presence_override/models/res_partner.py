# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models

from odoo.addons.bus.models.bus_presence import AWAY_TIMER
from odoo.addons.bus.models.bus_presence import DISCONNECTION_TIMER

from ..status_constants import ONLINE, AWAY, OFFLINE


class ResPartner(models.Model):

    _inherit = 'res.partner'

    im_status_custom = fields.Selection(
        selection=[
            (ONLINE, 'Online'),
            (AWAY, 'Away'),
            (OFFLINE, 'Offline'),
        ],
        string='Status',
        default=ONLINE,
    )

    @api.model
    def _get_partners_presence(self):
        """ This method gets any relevant partners' im status.

            Example:

                .. code-block:: python

                res = self.env['res.partner']._get_partners_presence()
                im_status = res.get(partner.id, OFFLINE)

            Returns:
                dict: Structured like so: {partner_id: im_status}

        """
        self.env.cr.execute(
            """
                SELECT
                    U.partner_id as id,
                    CASE WHEN age(now() AT TIME ZONE 'UTC', B.last_poll)
                            > interval %s THEN 'offline'
                        WHEN age(now() AT TIME ZONE 'UTC', B.last_presence)
                            > interval %s THEN 'away'
                        ELSE 'online'
                    END as status
                FROM bus_presence B
                    JOIN res_users U ON B.user_id = U.id
                WHERE U.partner_id IN %s AND U.active = 't'
            """,
            ("%s seconds" % DISCONNECTION_TIMER,
             "%s seconds" % AWAY_TIMER, tuple(self.ids))
        )
        all_status = self.env.cr.dictfetchall()
        all_status_dict = dict(
            ((status['id'], status['status']) for status in all_status)
        )
        return all_status_dict

    @api.multi
    def _compute_im_status(self):
        presence = self._get_partners_presence()

        for record in self:

            record.im_status = presence.get(record.id, OFFLINE)

            computed = record.im_status
            custom = record.im_status_custom

            if computed == OFFLINE:
                record.im_status_custom = computed

            elif custom in (AWAY, OFFLINE):
                record.im_status = custom

            elif computed == AWAY and custom == ONLINE:
                record.im_status_custom = computed
