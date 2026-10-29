# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

from odoo import _, api, fields, models


class SocialPost(models.Model):
    _inherit = "social.post"

    campaign_id = fields.Many2one("utm.campaign", domain=[("account_id", "!=", False)])

    def _default_account_ids(self):
        res = super()._default_account_ids()
        account_ids = (
            self.env["social.account"]
            .with_company(self.env.company)
            .search([("media_type", "=", "linkedin")])
        )
        if account_ids:
            return list(itertools.chain(account_ids.ids, res))
        return res

    @api.depends("account_ids")
    def _compute_message_info(self):
        message = super()._compute_message_info()
        for post in self:
            if (
                post.image_ids
                and post.video_ids
                and "linkedin" in post.account_ids.mapped("media_type")
            ):
                message_info = _(
                    "You have selected images and videos for this post. "
                    "However, the social media Linkedin does not allow "
                    "combining both types of content in the same post. Therefore, "
                    "only the images will be published. If you wish to publish a "
                    "video, please remove the images from this post or create a"
                    " separate post."
                )
                post.message_info = (
                    message + "\n" + message_info if post.message_info else message_info
                )
            else:
                post.message_info = message
        return message
