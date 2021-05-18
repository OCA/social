# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models
from lxml import etree, html
import re


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    def remove_href_odoo(self, value, remove_parent=True, remove_before=False):
        if len(value) < 20:
            return value
        # value can be bytes type; ensure we get a proper string
        if type(value) is bytes:
            value = value.decode()

        # https://regex101.com/r/o01Rfz/3
        has_odoo_link = re.search(r"(href\s*=\s*[\'\"]{1}(https?://)?(www|apps)?\.?odoo\.com(?!\.)\b)", value, flags=re.IGNORECASE)
        if has_odoo_link:
            tree = etree.HTML(
                value
            )  # html with broken links   tree = etree.fromstring(value) just xml

            # https://regex101.com/r/o01Rfz/5
            odoo_achors = tree.xpath(
                '//a[re:test(@href,"(^(https?://)?(www|apps)?\\.?odoo\\.com(?!\\.)\\b)")]',
                namespaces={'re': "http://exslt.org/regular-expressions"})
            for elem in odoo_achors:
                parent = elem.getparent()
                previous = elem.getprevious()

                if remove_before and not remove_parent and previous:
                    # remove 'using' that is before <a and after </span>
                    bytes_text = etree.tostring(
                        previous, pretty_print=True, method="html"
                    )
                    only_what_is_in_tags = bytes_text[: bytes_text.rfind(b">") + 1]
                    data_formatted = html.fromstring(only_what_is_in_tags)
                    parent.replace(previous, data_formatted)
                if remove_parent and len(parent.getparent()):
                    # anchor <a href odoo has a parent powered by that must be removed
                    parent.getparent().remove(parent)
                else:
                    if parent.tag == "td":  # also here can be powerd by
                        parent.getparent().remove(parent)
                    else:
                        parent.remove(elem)
            value = etree.tostring(tree, pretty_print=True, method="html")
            # etree can return bytes; ensure we get a proper string
            if type(value) is bytes:
                value = value.decode()
        # https://regex101.com/r/FLTxID/11
        return re.sub(r"(\s?(?:https?://)?(?:apps\.|www\.|(?<![\.\-\w\n]))odoo\.com(?!\.)\b[^\s\"<>]*|(?<!<|/)odoo(?![\w\-\.]{2,99}))", "", value, flags=re.IGNORECASE)

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
            engine=engine,
            add_context=add_context,
            post_process=post_process,
        )

        for key in res_ids:
            orginal_rendered[key] = self.remove_href_odoo(orginal_rendered[key])

        return orginal_rendered
