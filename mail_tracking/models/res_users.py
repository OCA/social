# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_messaging(self, store):
        res = super()._init_messaging(store)
        store.add(
            {
                "failed": {
                    "id": "failed",
                    "model": "mail.box",
                    "counter": self.env["mail.message"].get_failed_count(),
                }
            }
        )
        return res
