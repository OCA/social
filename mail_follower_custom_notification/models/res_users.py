# Copyright 2025 Hunki Enterprises BV <https://hunki-enterprises.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection(
        selection_add=[("email_and_inbox", "Handle by both Emails and in Odoo")],
        ondelete={"email_and_inbox": "set default"},
    )

    def _init_messaging(self):
        result = super()._init_messaging()
        result["notificationTypes"] = dict(
            self._fields["notification_type"]._description_selection(self.env)
        )
        return result
