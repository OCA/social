# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

from odoo import api, models
from odoo.exceptions import ValidationError


class SocialPost(models.Model):
    _inherit = "social.post"

    def _default_account_ids(self):
        res = super()._default_account_ids()
        account_ids = (
            self.env["social.account"]
            .with_company(self.env.company)
            .search([("media_type", "=", "x")])
        )
        if account_ids:
            return list(itertools.chain(account_ids.ids, res))
        return res

    @api.constrains("account_ids", "message", "image_ids", "video_ids", "campaign_id")
    def _check_account_ids(self):
        """
        This validation is done to check that X accounts do
        not have the same user associated, to avoid publication
        errors regarding repeating the same publication
        for an account (username).
        """
        for post in self:
            account_repeat = post.account_ids._get_group_account_username()
            if account_repeat and account_repeat[0].get("username_count", 0) > 1:
                raise ValidationError(
                    self.env._(
                        "There are X accounts with the "
                        f"same username ({account_repeat[0]['username']}),"
                        " please check to avoid spam errors."
                    )
                )

    @api.depends(
        "post_account_ids.like_count",
        "post_account_ids.comment_count",
        "post_account_ids.click_count",
        "post_account_ids.share_count",
        "post_account_ids.engagement",
        "post_account_ids.impression_count",
        "post_account_ids.retweet_count",
        "post_account_ids.quote_count",
    )
    def _compute_post_statistics(self):
        res = super()._compute_post_statistics()
        for post in self:
            post.count_post_interactions = (
                post.count_post_clicks
                + post.count_post_likes
                + post.count_post_comments
                + post.count_post_shares
                + sum(post.mapped("post_account_ids.retweet_count"))
                + sum(post.mapped("post_account_ids.quote_count"))
            )
        return res
