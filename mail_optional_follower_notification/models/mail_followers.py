# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api


class MailFollowers(models.Model):
    _inherit = 'mail.followers'

    @api.multi
    def _get_recipient_data(self, records, subtype_id, pids=None, cids=None):
        res = super()._get_recipient_data(
            records, subtype_id, pids=pids, cids=cids
        )
        if 'notify_followers' in self._context and not self._context.get(
            'notify_followers'
        ):
            return filter(
                lambda partner_id, partner_ids=pids: partner_id[0]
                in partner_ids, res
            )
        return res
