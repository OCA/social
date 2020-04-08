# Copyright 2017 David BEAL @ Akretion
# Copyright 2019 Camptocamp SA

# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models

try:
    from premailer import Premailer
except (ImportError, IOError) as err:  # pragma: no cover
    import logging

    _logger = logging.getLogger(__name__)
    _logger.debug(err)


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def render_post_process(self, html):
        html = super().render_post_process(html)
        return self._premailer_apply_transform(html)

    def _premailer_apply_transform(self, html):
        if not html.strip():
            return html
        premailer = Premailer(html=html, **self._get_premailer_options())
        return premailer.transform()

    def _get_premailer_options(self):
        return {}
