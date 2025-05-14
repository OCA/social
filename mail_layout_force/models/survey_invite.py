# Copyright 2025 Kencove (https://kencove.com).
# @author Mohamed Alkobrosli <malkobrosly.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SurveyInvite(models.TransientModel):
    _inherit = "survey.invite"

    def _send_mail(self, answer):
        context = {
            "default_email_layout_xmlid": self.template_id.force_email_layout_id.xml_id
        }
        if self.template_id and self.template_id.force_email_layout_id:
            email = super(SurveyInvite, self.with_context(**context))._send_mail(answer)
            return email
        return super()._send_mail(answer)
