from markupsafe import Markup

from odoo import api, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.onchange("template_id")
    def _onchange_template_id_wrapper(self):
        super()._onchange_template_id_wrapper()
        context = self._context
        if "is_quoted_reply" in context.keys() and context["is_quoted_reply"]:
            self.body += Markup(context["quote_body"])
        return
