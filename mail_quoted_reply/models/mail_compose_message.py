from markupsafe import Markup

from odoo import api, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.onchange("template_id")
    def _onchange_template_id_wrapper(self):
        super()._onchange_template_id_wrapper()
        context = self._context
        if "is_quoted_reply" in context.keys() and context["is_quoted_reply"]:
            self.body += Markup(context["quote_body"])
        return

    @api.model
    def get_record_data(self, values):
        result = super().get_record_data(values)
        subj = self._context.get("default_subject", False)
        if subj:
            result["subject"] = tools.ustr(subj)
        return result
