# Copyright 2026 Bernat Obrador APSL-Nagarro
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests

from odoo import http
from odoo.http import request

from odoo.addons.mail.controllers.discuss.gif import DiscussGifController


class GiphyGifController(DiscussGifController):
    """
    Inherit to add the logic for giphy api.
    It replace the calls needed to work with giphy.
    It will still use fields that are used for tenor
    for handeling favorites gifs
    """

    def _get_api_key(self):
        return (
            request.env["ir.config_parameter"].sudo().get_param("discuss.giphy_api_key")
        )

    def _normalize_gif(self, gif):
        images = gif.get("images", {})
        # Use fixed_height_small for thumbnails (similar to Tenor tinygif)
        tiny = (
            images.get("fixed_height_small")
            or images.get("fixed_height")
            or images.get("downsized")
            or images.get("original")
        )
        url = tiny.get("url") if tiny else None
        dims = [
            int(tiny.get("width", 0)) if tiny else 0,
            int(tiny.get("height", 0)) if tiny else 0,
        ]
        send_url = (
            images.get("original") or images.get("downsized") or tiny or {}
        ).get("url")
        return {
            "id": gif.get("id"),
            "title": gif.get("title") or "",
            "media_formats": {
                "tinygif": {
                    "url": url,
                    "dims": dims,
                }
            },
            "url": send_url,
        }

    @http.route("/discuss/gif/search", type="json", auth="user")
    def search(self, search_term, locale="en", country="US", position=None):
        api_key = self._get_api_key()
        if not api_key:
            return {"results": [], "next": None}
        ir_config = request.env["ir.config_parameter"].sudo()

        rating = ir_config.get_param("discuss.giphy_rating")
        rating = rating if rating != "any" else ""
        params = {
            "api_key": api_key,
            "q": search_term,
            "limit": ir_config.get_param("discuss.giphy_gif_limit"),
            "rating": rating,
            "offset": int(position or 0),
            "lang": locale[:2] if locale else "en",
            "country_code": country,
        }
        resp = requests.get(
            "https://api.giphy.com/v1/gifs/search", params=params, timeout=8
        )
        resp.raise_for_status()
        data = resp.json()
        results = [self._normalize_gif(g) for g in data.get("data", [])]
        pagination = data.get("pagination", {})
        next_offset = None
        if pagination:
            offset = pagination.get("offset") or 0
            count = pagination.get("count") or 0
            total_count = pagination.get("total_count") or 0
            if offset + count < total_count:
                next_offset = offset + count
        return {"results": results, "next": next_offset}

    @http.route("/discuss/gif/categories", type="json", auth="user")
    def categories(self, locale="en", country="US"):
        # Giphy does not have a stable categories endpoint like tenor,
        # so we return an empty list.
        return {"tags": []}

    def _gif_posts(self, ids):
        api_key = self._get_api_key()
        if not api_key or not ids:
            return []
        resp = requests.get(
            "https://api.giphy.com/v1/gifs",
            params={"api_key": api_key, "ids": ",".join(ids)},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return [self._normalize_gif(g) for g in data.get("data", [])]

    @http.route("/discuss/gif/favorites", type="json", auth="user")
    def get_favorites(self, offset=0):
        gif_ids = (
            request.env["discuss.gif.favorite"]
            .sudo()
            .search([("create_uid", "=", request.env.user.id)], limit=20, offset=offset)
            .mapped("tenor_gif_id")
        )
        return (self._gif_posts(gif_ids),)
