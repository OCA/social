# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# Copyright 2021 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from lxml import html as htmltree

from odoo import _, api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.model
    def _debrand_body(self, html):
        using_word = _("using")
        odoo_word = _("Odoo")
        html = re.sub(using_word + "(.*)[\r\n]*(.*)>" + odoo_word + r"</a>.", "", html)
        powered_by = _("Powered by")
        if powered_by not in html:
            by = _("by")
            company_web = _(self.env.user.company_id.website)
            html = re.sub("Sent[\n]", "", html)
            root = htmltree.fromstring(html)
            by_elements = root.xpath("//*[text()[contains(.,'%s')]]" % by)
            for elem in by_elements:
                if any(
                    [
                        company_web in child.get("href", "")
                        for child in elem.getchildren()
                    ]
                ):
                    for child in elem.getchildren():
                        elem.remove(child)
                    elem.text = None
            return htmltree.tostring(root).decode("utf-8")
        root = htmltree.fromstring(html)
        powered_by_elements = root.xpath("//*[text()[contains(.,'%s')]]" % powered_by)
        for elem in powered_by_elements:
            # make sure it isn't a spurious powered by
            if any(
                [
                    "www.odoo.com" in child.get("href", "")
                    for child in elem.getchildren()
                ]
            ):
                for child in elem.getchildren():
                    elem.remove(child)
                elem.text = None
        return htmltree.tostring(root).decode("utf-8")

    @api.model
    def _render_template_postprocess(self, rendered):
        rendered = super()._render_template_postprocess(rendered)
        for res_id, html in rendered.items():
            rendered[res_id] = self._debrand_body(html)
            return rendered
