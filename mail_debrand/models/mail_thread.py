# Copyright 2019 Eficent Business and IT Consulting Services S.L.
#   Lois Rilo <lois.rilo@eficent.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _replace_local_links(self, html, base_url=None):
        html = super()._replace_local_links(html, base_url=base_url)
        lang = False
        if {'default_template_id', 'default_model', 'default_res_id'} \
                <= self.env.context.keys():
            template = self.env["mail.template"].browse(
                self.env.context['default_template_id'])
            if template.lang:
                lang = template._render_template(template.lang,
                                                 self.env.context['default_model'],
                                                 self.env.context['default_res_id'])
            elif template._context.get('lang', False):
                lang = template._context.get('lang')
        html_debranded = self.env["mail.template"]._debrand_body(html, lang)
        return html_debranded
