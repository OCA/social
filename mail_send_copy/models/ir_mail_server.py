# Copyright (C) 2014 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from email.utils import COMMASPACE


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, *args, **kwargs):
        do_not_send_copy = self.env.context.get("do_not_send_copy", False)
        if not do_not_send_copy:
            if message["Bcc"]:
                message["Bcc"] = message["Bcc"].join(
                    COMMASPACE, message["From"])
            else:
                message["Bcc"] = message["From"]
        return super().send_email(message, *args, **kwargs)
