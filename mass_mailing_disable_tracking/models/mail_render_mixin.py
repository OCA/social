# SPDX-FileCopyrightText: 2025 hugues de keyzer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from odoo import api, models

from .res_config_settings import TRACK_LINKS_PARAMETER


class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    @api.model
    def _shorten_links(self, html, link_tracker_vals, blacklist=None, base_url=None):
        if self.env["ir.config_parameter"].sudo().get_param(TRACK_LINKS_PARAMETER):
            return super()._shorten_links(html, link_tracker_vals, blacklist, base_url)
        return html

    @api.model
    def _shorten_links_text(
        self, content, link_tracker_vals, blacklist=None, base_url=None
    ):
        if self.env["ir.config_parameter"].sudo().get_param(TRACK_LINKS_PARAMETER):
            return super()._shorten_links_text(
                content, link_tracker_vals, blacklist, base_url
            )
        return content
