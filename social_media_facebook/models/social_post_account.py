# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialPostAccount(models.Model):
    _inherit = "social.post.account"

    facebook_post_id = fields.Char(string="Facebook Post ID")

    def _action_post(self):
        super()._action_post()
        if self.account_id.media_type == "facebook":
            post_id = self.account_id._action_post(
                message=self.message,
                image_ids=self.image_ids,
                video_ids=self.video_ids,
            )
            if post_id:
                self.write(
                    {
                        "facebook_post_id": post_id,
                        "post_account_url": f"https://www.facebook.com/{post_id}",
                        "published_date": fields.Datetime.now(),
                        "state": "posted",
                    }
                )
            else:
                self.write(
                    {
                        "state": "failed",
                        "failed_description": "Failed to post on Facebook",
                    }
                )
