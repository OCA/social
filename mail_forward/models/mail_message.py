# Copyright 2024 Tecnativa - Carlos Lopez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, models
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = "mail.message"

    def action_wizard_forward(self):
        view = self.env.ref("mail_forward.mail_compose_message_forward_form")
        action = self.env["ir.actions.actions"]._for_xml_id(
            "mail.action_email_compose_message_wizard"
        )
        action["name"] = _("Forward Message")
        action["view_mode"] = view.type
        action["views"] = [(view.id, view.type)]
        action["context"] = {
            "default_model": self.model,
            "default_res_id": self.res_id,
            "default_composition_mode": "comment",
            "default_body": self._build_message_body_for_forward(),
            "default_attachment_ids": self.attachment_ids.ids,
            "default_is_log": False,
            "default_notify": True,
            "force_email": True,
            "message_forwarded_id": self.id,
        }
        return action

    def _build_message_body_for_forward(self):
        partner_emails = [
            partner.email_formatted
            for partner in self.partner_ids
            if partner.email_formatted
        ]
        return """
            <br/><br/><br/>
            {str_forwarded_message}<br/>
            {str_from}: {email_from}<br/>
            {str_date}: {date}<br/>
            {str_subject}: {subject}<br/>
            {str_to}: {to}<br/>
            <br/><br/>
            {body}
        """.format(
            str_forwarded_message=_("---------- Forwarded message ---------"),
            email_from=self.email_from,
            date=format_datetime(self.env, self.date),
            subject=self.subject,
            to=", ".join(partner_emails),
            str_date=_("Date"),
            str_subject=_("Subject"),
            str_from=_("From"),
            str_to=_("To"),
            body=self.body,
        )
