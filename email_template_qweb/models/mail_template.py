# Copyright 2016-2024 Therp BV <http://therp.nl>
# Copyright 2024 ForgeFlow S.L. (https://www.forgeflow.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models, tools
from odoo.tools import format_datetime


class MailTemplate(models.Model):
    _inherit = "mail.template"

    body_type = fields.Selection(
        [("qweb", "QWeb"), ("qweb_view", "QWeb View")],
        "Body templating engine",
        default="qweb",
        required=True,
    )
    body_view_id = fields.Many2one("ir.ui.view", domain=[("type", "=", "qweb")])
    body_view_arch = fields.Text(related="body_view_id.arch")

    def _generate_template(self, res_ids, render_fields, find_or_create_partners=False):
        render_results = super()._generate_template(
            res_ids, render_fields, find_or_create_partners=find_or_create_partners
        )

        if self.body_type == "qweb_view":
            if "body_html" in render_fields:
                IrQweb = self.env["ir.qweb"]
                for res_id in res_ids:
                    record = self.env[self.model].browse(res_id)
                    custom_context = {
                        "object": record,
                        "email_template": self,
                        "format_datetime": lambda dt,
                        tz=False,
                        dt_format=False,
                        lang_code=False: format_datetime(
                            self.env, dt, tz, dt_format, lang_code
                        ),
                    }
                    body_html = IrQweb._render(self.body_view_id.id, custom_context)
                    body_html = tools.ustr(body_html)
                    render_results[res_id]["body_html"] = body_html

        return render_results
