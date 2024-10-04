from markupsafe import Markup

from odoo import api, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    @api.depends_context("is_quoted_reply")
    def _compute_body(self):
        res = super()._compute_body()
        for composer in self:
            context = composer._context
            if context.get("is_quoted_reply"):
                if composer.body:
                    composer.body += Markup(context["quote_body"])
                else:
                    composer.body = Markup(context["quote_body"])
        return res

    @api.depends(
        "composition_mode",
        "model",
        "parent_id",
        "record_name",
        "res_domain",
        "res_ids",
        "template_id",
    )
    @api.depends_context("default_subject")
    def _compute_subject(self):
        res = super()._compute_subject()
        for composer in self:
            subj = composer._context.get("default_subject", False)
            if subj:
                composer.subject = tools.ustr(subj)
        return res
