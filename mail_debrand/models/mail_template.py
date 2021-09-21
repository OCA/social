# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from lxml import html as htmltree
import re
from odoo import _, api, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    @api.model
    def _debrand_body(self, html, translate_=_):
        if not self.env.context.get("debrand_notranslate"):
            html = self.with_context(debrand_notranslate=True)._debrand_body(
                html, lambda x: x
            )

        using_word = translate_("using")
        odoo_word = translate_("Odoo")
        html = re.sub(
            using_word + "(.*)[\r\n]*(.*)>" + odoo_word + r"</a>",
            "",
            html,
        )
        powered_by = translate_("Powered by")
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

    @api.multi
    def send_mail(
        self,
        res_id,
        force_send=False,
        raise_exception=False,
        email_values=None,
        notif_layout=False,
    ):
        """When `notif_layout` is `False`, no `render_post_process` nor
        `_replace_local_links` are called. That's why we need to override
        `generate_email`
        """
        return super(
            MailTemplate, self.with_context(debrand_generate_email=not notif_layout)
        ).send_mail(res_id, force_send, raise_exception, email_values, notif_layout)

    @api.multi
    def generate_email(self, res_ids, fields=None):
        res = super().generate_email(res_ids, fields)
        if self.env.context.get("debrand_generate_email") and res.get("body_html"):
            res["body_html"] = self._debrand_body(res.get("body_html"))
        return res
