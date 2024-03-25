# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# Copyright 2023 Abraham Anes <abrahamanes@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, auto_commit=False):
        # OVERRIDE to force the email_layout_xmlid defined on the mail.template
        for rec in self:
            if rec.template_id.force_email_layout_id:
                rec.email_layout_xmlid = rec.template_id.force_email_layout_id.xml_id
        return super(MailComposer, self)._action_send_mail(auto_commit=auto_commit)
