# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class MailNotification(models.Model):
    _inherit = "mail.notification"

    @api.model
    def _gc_notifications(self, max_age_days=180):
        res = super()._gc_notifications(max_age_days=max_age_days)
        # Extend GC to also delete notifications in error
        read_date = fields.Datetime.subtract(fields.Datetime.now(), days=max_age_days)
        domain = [
            ("is_read", "=", True),
            ("read_date", "<", read_date),
            ("notification_status", "in", ("bounce", "exception")),
        ]
        self.search(domain).unlink()
        return res
