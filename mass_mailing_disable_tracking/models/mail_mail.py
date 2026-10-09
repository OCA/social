# SPDX-FileCopyrightText: 2025 hugues de keyzer
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

import werkzeug.urls
from markupsafe import Markup

from odoo import api, models, tools

from .res_config_settings import TRACK_LINKS_PARAMETER, TRACK_OPEN_PARAMETER

TRACKING_LINK_PREFIX = "/r/"
DO_NOT_REPLACE_PLACEHOLDER = "/__do_not_replace__/"
DUMMY_TRACKING_URL = "https://this.is.a.dummy.tracking.url/"


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _replace_in_html(self, html, to_replace, value):
        # this comes from mail.render.mixin._replace_local_links() from the
        # mail module.
        if not html:
            return html
        wrapper = Markup if isinstance(html, Markup) else str
        html = str(html or "")
        return wrapper(html.replace(to_replace, value))

    @api.model
    def _replace_tracking_like_links(self, body, to_replace, value):
        # this is the same mechanism to find and replace links as used in the
        # _prepare_outgoing_body() method from the mass_mailing module.
        for match in set(re.findall(tools.mail.URL_REGEX, body)):
            href = match[0]
            url = match[1]
            parsed = werkzeug.urls.url_parse(url, scheme="http")
            if parsed.scheme.startswith("http") and parsed.path.startswith(to_replace):
                new_href = href.replace(url, url.replace(to_replace, value))
                body = self._replace_in_html(body, href, new_href)
        return body

    def _get_tracking_url(self):
        if self.env["ir.config_parameter"].sudo().get_param(TRACK_OPEN_PARAMETER):
            return super()._get_tracking_url()
        # return a dummy tracking url that can be replaced afterwards. it must
        # be a full url, otherwise it will be considered as a local url and
        # converted.
        return DUMMY_TRACKING_URL

    def _prepare_outgoing_body(self):
        # mail.mail._prepare_outgoing_body() in the mass_mailing module does 2
        # things:
        # 1. convert tracking links by appending a mailing.trace id to them.
        # 2. add an tracking image at the end of the html body.
        # it does these things only if its mailing_id and mailing_trace_ids
        # fields are set.
        self.ensure_one()
        ir_config_parameter_model = self.env["ir.config_parameter"].sudo()
        track_open = ir_config_parameter_model.get_param(TRACK_OPEN_PARAMETER)
        track_links = ir_config_parameter_model.get_param(TRACK_LINKS_PARAMETER)
        if (
            not self.mailing_id
            or not self.mailing_trace_ids
            or (track_open and track_links)
        ):
            return super()._prepare_outgoing_body()
        body_html = self.body_html
        if not track_links:
            # ensure that there are no links that look like tracking links to
            # avoid them being replaced.
            self.body_html = self._replace_tracking_like_links(
                self.body_html, TRACKING_LINK_PREFIX, DO_NOT_REPLACE_PLACEHOLDER
            )
        body = super()._prepare_outgoing_body()
        if not track_links:
            self.body_html = body_html
            body = self._replace_tracking_like_links(
                body, DO_NOT_REPLACE_PLACEHOLDER, TRACKING_LINK_PREFIX
            )
        if not track_open:
            body = self._replace_in_html(
                body, f'\n<img src="{DUMMY_TRACKING_URL}"/>\n', ""
            )
        return body
