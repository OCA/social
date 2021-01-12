# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import re

from lxml import etree

from odoo import api, models


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _render_template(
        self,
        template_src,
        model,
        res_ids,
        engine="jinja",
        add_context=None,
        post_process=False,
    ):
        """replace anything that is with odoo in templates
        if is a <a that contains odoo will delete it completly
        original:
         Render the given string on records designed by model / res_ids using
        the given rendering engine. Currently only jinja is supported.

        :param str template_src: template text to render (jinja) or  (qweb)
          this could be cleaned but hey, we are in a rush
        :param str model: model name of records on which we want to perform rendering
        :param list res_ids: list of ids of records (all belonging to same model)
        :param string engine: jinja
        :param post_process: perform rendered str / html post processing (see
          ``_render_template_postprocess``)

        :return dict: {res_id: string of rendered template based on record}"""
        orginal_rendered = super()._render_template(
            template_src,
            model,
            res_ids,
            engine="jinja",
            add_context=None,
            post_process=False,
        )

        for key in res_ids:
            value = orginal_rendered[key]
            if len(value) < 20:
                continue
            has_odoo_link = re.search(r"<a\s(.*)odoo\.com", value, flags=re.IGNORECASE)
            if has_odoo_link:
                tree = etree.HTML(value)  # html with brlken links
                #                tree = etree.fromstring(value) just xml
                odoo_achors = tree.xpath('//a[contains(@href,"odoo.com")]')
                for elem in odoo_achors:
                    parent = elem.getparent()
                    if (
                        parent.getparent()
                    ):  # anchor <a href odoo has a parent and another one
                        parent.getparent().remove(parent)
                    else:
                        parent.remove(elem)
                orginal_rendered[key] = etree.tostring(
                    tree, pretty_print=True, method="html"
                )
            if type(orginal_rendered[key]) is str:
                orginal_rendered[key] = re.sub(
                    "[^(<)(</)]odoo", "", orginal_rendered[key], flags=re.IGNORECASE
                )
            elif type(orginal_rendered[key]) is bytes:
                orginal_rendered[key] = re.sub(
                    b"[^(<)(</)]odoo", b"", orginal_rendered[key], flags=re.IGNORECASE
                )

        return orginal_rendered
