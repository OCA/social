# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailGuest(models.Model):
    _inherit = "mail.guest"

    def _init_messaging(self):
        """For discuss"""
        values = super()._init_messaging()
        values["failed_counter"] = False
        return values
