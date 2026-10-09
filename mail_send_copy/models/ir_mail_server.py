# Copyright (C) 2014 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from email.utils import COMMASPACE

from odoo import api, models

_logger = logging.getLogger(__name__)


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(self, message, *args, **kwargs):
        do_not_send_copy = self.env.context.get("do_not_send_copy", False)
        if not do_not_send_copy:
            # Get existing Bcc recipients (if any)
            bcc = message.get("Bcc", "")
            from_addr = message.get("From", "")

            # Combine existing Bcc with From address
            if bcc:
                all_bcc = COMMASPACE.join([bcc, from_addr])
            else:
                all_bcc = from_addr

            # Set the combined Bcc
            if "Bcc" in message:
                message.replace_header("Bcc", all_bcc)
            else:
                message.add_header("Bcc", all_bcc)

        return super().send_email(message, *args, **kwargs)
