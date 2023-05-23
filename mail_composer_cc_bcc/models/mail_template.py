# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, tools

from ..wizards.mail_compose_message import CC_BCC_FIELDS


class MailTemplate(models.Model):
    _inherit = "mail.template"

    email_bcc = fields.Char(
        "Bcc", help="Blind cc recipients (placeholders may be used here)"
    )

    def generate_recipients(self, results, res_ids):
        res = super().generate_recipients(results, res_ids)
        is_from_composer = self.env.context.get("is_from_composer", False)
        if not is_from_composer or not (self.email_cc or self.email_bcc):
            return res
        ctx = {"tpl_partners_only": False}
        ctx.update(self.env.context)
        tmpl_ctx = super().with_context(**ctx)
        template_values = {}
        tmpl_ctx._render_fields(res_ids, CC_BCC_FIELDS.keys(), template_values)
        for res_id, values in template_values.items():
            email_cc_bcc = tools.email_split(values["email_cc"])
            email_cc_bcc += tools.email_split(values["email_bcc"])
            for_emails = [("email", "in", email_cc_bcc)]
            partner_cc_bcc_ids = self.env["res.partner"].search(for_emails).ids
            if not partner_cc_bcc_ids:
                continue
            res[res_id]["partner_ids"] = [
                _id
                for _id in res[res_id]["partner_ids"]
                if _id not in partner_cc_bcc_ids
            ]
        return res

    def _render_fields(self, res_ids, field_names, results):
        template = self
        template_res_ids = res_ids
        for field in field_names:
            generated_field_values = template._render_field(
                field,
                template_res_ids,
                options={"render_safe": field == "subject"},
                post_process=(field == "body_html"),
            )
            for res_id, field_value in generated_field_values.items():
                results.setdefault(res_id, dict())[field] = field_value
        return results
