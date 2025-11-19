# Copyright (C) 2014 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from email.utils import COMMASPACE

from odoo import api, models, tools


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, *args, **kwargs):
        do_not_send_copy = self.env.context.get("do_not_send_copy", False)
        sender_emails = tools.email_normalize_all(message["From"])
        if do_not_send_copy or not sender_emails:
            return super().send_email(message, *args, **kwargs)
        # Get existing Bcc recipients (if any)
        bcc = message["Bcc"]
        del message["Bcc"]
        # Combine existing Bcc with From address
        message["Bcc"] = COMMASPACE.join(filter(None, [bcc, *sender_emails]))
        validated_to = self.env.context.get("send_validated_to")
        if not validated_to:
            return super().send_email(message, *args, **kwargs)
        server = self.with_context(send_validated_to=validated_to + sender_emails)
        return super(IrMailServer, server).send_email(message, *args, **kwargs)
