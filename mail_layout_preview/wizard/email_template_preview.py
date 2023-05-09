# Copyright 2020 Simone Orsi - Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, fields, models


class MailTemplatePreview(models.TransientModel):
    _inherit = "mail.template.preview"

    _url_pattern = "/email-preview/{model}/{templ_id}/{rec_id}/"

    layout_preview_url = fields.Char(
        string="Full layout preview", compute="_compute_layout_preview_url"
    )

    @api.depends("resource_ref", "model_id", "mail_template_id")
    def _compute_layout_preview_url(self):
        for rec in self:
            if rec.mail_template_id and rec.resource_ref:
                rec.layout_preview_url = self._url_pattern.format(
                    model=rec.model_id.model,
                    templ_id=rec.mail_template_id.id,
                    rec_id=rec.resource_ref.id,
                )
            else:
                rec.layout_preview_url = ""
