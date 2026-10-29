# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo import api, fields, models


class SocialPostMixin(models.AbstractModel):
    _name = "social.post.mixin"
    _description = "Social Network Post Mixin"

    image_urls = fields.Char(compute="_compute_image_urls", store=True)
    video_urls = fields.Char(compute="_compute_video_urls", store=True)

    @api.depends(lambda self: ["image_ids"])
    def _compute_image_urls(self):
        for post in self:
            post.image_urls = json.dumps(
                [f"/web/image/{image_id}" for image_id in post.image_ids.ids]
            )

    @api.depends(lambda self: ["video_ids"])
    def _compute_video_urls(self):
        for post in self:
            post.video_urls = json.dumps(
                [f"/web/content/{video_id}" for video_id in post.video_ids.ids]
            )
