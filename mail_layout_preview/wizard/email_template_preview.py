# Copyright 2020 Simone Orsi - Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class TemplatePreview(models.TransientModel):
    _inherit = "email_template.preview"

    _url_pattern = "/email-preview/{model}/{templ_id}/{rec_id}/"

    layout_preview_url = fields.Char(
        string="Full layout preview", compute="_compute_layout_preview_url"
    )

    @api.depends("res_id")
    def _compute_layout_preview_url(self):
        for rec in self:
            if self.env.context.get("template_id"):
                rec.layout_preview_url = self._url_pattern.format(
                    model=rec.model_id.model,
                    templ_id=self.env.context["template_id"],
                    rec_id=rec.res_id,
                )
            else:
                rec.layout_preview_url = ""
