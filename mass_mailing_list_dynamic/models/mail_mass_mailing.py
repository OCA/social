# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    def send_mail(self):
        """Sync dynamic lists before sending mailings to them."""
        self.contact_list_ids.action_sync()
        return super(MassMailing, self).send_mail()
