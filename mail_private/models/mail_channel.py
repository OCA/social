# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.multi
    def _notify(self, message):
        if message.mail_group_id:
            return
        return super()._notify(message)
