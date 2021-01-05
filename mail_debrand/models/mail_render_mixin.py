# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    def _replace_local_links(self, html, base_url=None):
        html = super()._replace_local_links(html, base_url=base_url)
        html_debranded = self.env["mail.template"]._debrand_body(html)
        return html_debranded
