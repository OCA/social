# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime
from email.utils import COMMASPACE

from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _tracking_email_prepare(self, email):
        """Prepare email.tracking.email record values"""
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        email_to_list = email.get("email_to", [])
        email_to = COMMASPACE.join(email_to_list)
        return {
            "name": self.subject,
            "timestamp": f"{ts:.6f}",
            "time": fields.Datetime.to_string(dt),
            "mail_id": self.id,
            "mail_message_id": self.mail_message_id.id,
            "partner_id": (email.get("partner_id") or self.env["res.partner"]).id,
            "recipient": email_to,
            "sender": self.email_from,
        }

    def _prepare_outgoing_list(
        self, mail_server=False, recipients_follower_status=None
    ):
        """Creates the mail.tracking.email record and adds the image tracking
        to the email. Please note that because we can't add mail headers in this
        function, the added tracking image will later (IrMailServer.build_email)
        also be used to extract the mail.tracking.email record id and to set the
        X-Odoo-MailTracking-ID header there.
        """
        emails = super()._prepare_outgoing_list(mail_server, recipients_follower_status)
        for email in emails:
            vals = self._tracking_email_prepare(email)
            tracking_email = self.env["mail.tracking.email"].sudo().create(vals)
            tracking_email.tracking_img_add(email)
        return emails
