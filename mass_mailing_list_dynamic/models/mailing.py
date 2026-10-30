# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MassMailing(models.Model):
    _inherit = "mailing.mailing"

    def action_launch(self):
        # Do the sync prior to putting the mailing in queue. Otherwise, if an error
        # raises, the user won't be able to detect it and the Mass Mailing queue cron
        # will be blocked forever.
        self.contact_list_ids.action_sync()
        return super().action_launch()
