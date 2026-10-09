from markupsafe import Markup

from odoo import api, fields, models, tools


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    is_reply_readonly = fields.Boolean(default=True, string="Reply Readonly")
    reply_body = fields.Html(default="", string="Reply body")
    is_separate_body = fields.Boolean(compute="_compute_is_separate_body")

    @api.depends("composition_mode", "model", "res_domain", "res_ids", "template_id")
    @api.depends_context("is_quoted_reply")
    def _compute_body(self):
        res = super()._compute_body()
        for composer in self:
            context = composer._context
            if context.get("is_quoted_reply"):
                if self.is_separate_body:
                    self.reply_body = context["quote_body"]
                else:
                    if self.body:
                        self.body += Markup(context["quote_body"])
                    else:
                        self.body = Markup(context["quote_body"])
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

    @api.onchange("is_reply_readonly")
    def _onchange_is_reply_readonly(self):
        if self.reply_body:
            self.reply_body = Markup(self.reply_body)

    @api.depends("reply_body")
    def _compute_is_separate_body(self):
        if self._context.get("is_quoted_reply", False):
            parameter_string = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mail_quoted_reply.separate_reply_body", "")
            )
            self.is_separate_body = parameter_string.lower() not in ["", "false", "0"]
        else:
            self.is_separate_body = False

    def _prepare_mail_values(self, res_ids):
        results = super()._prepare_mail_values(res_ids)
        if self.is_separate_body and self.reply_body:
            for res_id in res_ids:
                values = results.get(res_id)
                reply_body = Markup(self.reply_body)
                values.update({"body": values.get("body") + reply_body})
        return results
