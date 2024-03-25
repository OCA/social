# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResUsers(models.Model):

    _inherit = "res.users"

    broker_ids = fields.Many2many("mail.broker")

    def _init_messaging(self):
        result = super()._init_messaging()
        result["brokers"] = self.broker_ids.broker_info()
        return result
