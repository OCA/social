# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.home import Home as WebHome


class Home(WebHome):
    def _get_allowed_robots_routes(self):
        """Allow Meta to fetch tokenized Instagram media URLs.

        Core ``robots.txt`` is ``Disallow: /``. Instagram's Send Messages
        fetcher respects that and returns HTTP 400 / 2018007 when it
        cannot download the file.

        :return: URL path prefixes allowed for crawlers
        :rtype: list
        """
        routes = super()._get_allowed_robots_routes()
        path = "/mail_gateway_instagram/content"
        if path not in routes:
            return list(routes) + [path]
        return routes

    @http.route()
    def robots(self, **kwargs):
        """Put Instagram media ``Allow`` before core ``Disallow: /``.

        facebookexternalhit first-matches robots.txt, so the core order
        (``Disallow: /`` then ``Allow``) still blocks the file.

        :return: robots.txt HTTP response
        :rtype: odoo.http.Response
        """
        allowed_routes = self._get_allowed_robots_routes()
        allow_lines = [f"Allow: {route}" for route in allowed_routes]
        lines = (
            ["User-agent: facebookexternalhit"]
            + allow_lines
            + ["", "User-agent: *"]
            + allow_lines
            + ["Disallow: /"]
        )
        return request.make_response(
            "\n".join(lines),
            [("Content-Type", "text/plain")],
        )
