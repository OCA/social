# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    def get_remaining_recipients(self):
        """When evaluating remaining recipients we must resync the list in
           advance to avoid missing recipients due to domain change or new
           partners fitting into the conditions"""
        self.contact_list_ids.action_sync()
        return super().get_remaining_recipients()
