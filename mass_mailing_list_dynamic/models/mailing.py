# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing(models.Model):
    _inherit = "mailing.mailing"

    def _get_remaining_recipients(self):
        """When evaluating remaining recipients we must resync the list in
        advance to avoid missing recipients due to domain change or new
        partners fitting into the conditions"""
        self.contact_list_ids.action_sync()
        return super()._get_remaining_recipients()
