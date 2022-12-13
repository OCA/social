# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailMessage(models.Model):

    _inherit = "mail.message"

    def _prep_quoted_reply_body(self):
        return """
            <div>
                <br/>
                <br/>
            </div>
            <br/>
            <blockquote style="padding-right:0px; padding-left:5px; border-left-color: #000;
            margin-left:5px; margin-right:0px;border-left-width: 2px; border-left-style:solid">
            From: {email_from}<br/>
            Date: {date}<br/>
            Subject: {subject}<br/>
            {body}
            </blockquote>
        """.format(
            email_from=self.email_from,
            date=self.date,
            subject=self.subject,
            body=self.body,
        )

    def reply_message(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mail.action_email_compose_message_wizard"
        )
        action["context"] = {
            "default_model": self.model,
            "default_res_id": self.res_id,
            "default_composition_mode": "comment",
            "quote_body": self._prep_quoted_reply_body(),
            "default_is_log": False,
            "is_log": False,
            "is_quoted_reply": True,
            "default_notify": True,
            "force_email": True,
            "default_partner_ids": [(6, 0, self.partner_ids.ids)],
        }
        return action
