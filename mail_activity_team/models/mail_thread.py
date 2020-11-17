# Copyright 2020 sewisoft, guenter.selbert
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None,
                          force=True):
        """ filter none """
        if partner_ids:
            partner_ids = [pid for pid in partner_ids if pid]
        return super().message_subscribe(
            partner_ids=partner_ids,
            channel_ids=channel_ids,
            subtype_ids=subtype_ids,
            force=force
        )
