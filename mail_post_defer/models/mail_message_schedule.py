# Copyright 2024 Moduon Team S.L. <info@moduon.team>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class MailMessageSchedule(models.Model):
    _inherit = "mail.message.schedule"

    def _send_notifications(self, default_notify_kwargs=None):
        """Avoid deferring notifications when they should be sent."""
        _self = self.with_context(mail_defer_seconds=0)
        return super(MailMessageSchedule, _self)._send_notifications(
            default_notify_kwargs=default_notify_kwargs
        )
