# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _prep_quoted_reply_body(self):
        return """
            <div style="margin: 0px; padding: 0px;">
            <p style="margin:0px 0 12px 0;box-sizing:border-box;">
            <br />
            </p>
            {signature}
            <br />
            <br />
            <blockquote style="padding-right:0px; padding-left:5px;
            border-left-color: #000; margin-left:5px; margin-right:0px;
            border-left-width: 2px; border-left-style:solid">
            {str_from}: {email_from}<br/>
            {str_date}: {date}<br/>
            {str_subject}: {subject}<br/>
            {body}
            </blockquote>
            </div>
        """.format(
            email_from=self.email_from,
            date=format_datetime(self.env, self.date),
            subject=self.subject,
            body=self.body,
            signature=self.env.user.signature,
            str_date=_("Date"),
            str_subject=_("Subject"),
            str_from=_("From"),
        )

    def _default_reply_partner(self):
        return self.env["res.partner"].find_or_create(self.email_from).ids

    def reply_message(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mail.action_email_compose_message_wizard"
        )
        action["context"] = {
            "default_model": self.model,
            "default_res_ids": [self.res_id],
            "default_composition_mode": "comment",
            "quote_body": self._prep_quoted_reply_body(),
            "default_is_log": False,
            "is_log": False,
            "is_quoted_reply": True,
            "default_notify": True,
            "force_email": True,
            "default_partner_ids": self._default_reply_partner(),
        }

        # If the original message had a subject, we use it as a base for the
        # new subject, adding a "Re:" at the beginning.
        if self.subject:
            action["context"]["default_subject"] = f"Re: {self.subject}"

        return action
