# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        result = super()._notify_get_recipients(message, msg_vals, **kwargs)
        to_add = []
        for recipient in result:
            if recipient["notif"] == "email_and_inbox":
                recipient["notif"] = "email"
                to_add.append(dict(recipient, notif="inbox"))
        return result + to_add
