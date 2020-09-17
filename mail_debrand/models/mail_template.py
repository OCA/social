# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re

from lxml import html as htmltree

from odoo import _, api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.model
    def _debrand_translated_words(self):
        def _get_translated(word):
            return self.env["ir.translation"]._get_source(
                "ir.ui.view,arch_db", "model_terms", self.env.lang, word
            )

        odoo_word = _get_translated("Odoo") or _("Odoo")
        powered_by = _get_translated("Powered by") or _("Powered by")
        using_word = _get_translated("using") or _("using")
        return odoo_word, powered_by, using_word

    @api.model
    def _debrand_body(self, html):
        odoo_word, powered_by, using_word = self._debrand_translated_words()
        html = re.sub(using_word + "(.*)[\r\n]*(.*)>" + odoo_word + r"</a>", "", html)
        if powered_by not in html:
            return html
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
    def render_post_process(self, html):
        html = super().render_post_process(html)
        return self._debrand_body(html)
