# Copyright 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models, tools


class MailTemplate(models.Model):
    _inherit = "mail.template"

    body_type = fields.Selection(
        [("jinja2", "Jinja2"), ("qweb", "QWeb")],
        "Body templating engine",
        default="jinja2",
        required=True,
    )
    body_view_id = fields.Many2one("ir.ui.view", domain=[("type", "=", "qweb")])
    body_view_arch = fields.Text(related="body_view_id.arch")

    def generate_email(self, res_ids, fields):
        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False
        result = super(MailTemplate, self).generate_email(res_ids, fields=fields)
        for lang, (_template, _template_res_ids) in self._classify_per_lang(
            res_ids
        ).items():
            self_with_lang = self.with_context(lang=lang)
            for res_id in res_ids:
                if self.body_type == "qweb" and (not fields or "body_html" in fields):
                    for record in self_with_lang.env[self.model].browse(res_id):
                        body_html = self_with_lang.body_view_id._render(
                            {"object": record, "email_template": self_with_lang}
                        )
                        # Some wizards, like when sending a sales order, need this
                        # fix to display accents correctly
                        body_html = tools.ustr(body_html)
                        result[res_id][
                            "body_html"
                        ] = self_with_lang._render_template_postprocess(
                            {res_id: body_html}
                        )[
                            res_id
                        ]
                        result[res_id]["body"] = tools.html_sanitize(
                            result[res_id]["body_html"]
                        )
        return result if multi_mode else result[res_ids[0]]
