# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class SocialPostAccount(models.Model):
    _name = "social.post.account"
    _inherit = ["mail.thread", "social.post.mixin"]
    _description = "Social Post Account"
    _rec_name = "message"

    post_id = fields.Many2one("social.post", ondelete="cascade")
    active = fields.Boolean(default=True)
    account_id = fields.Many2one("social.account", ondelete="restrict", required=True)
    media_id = fields.Many2one(
        "social.media", related="account_id.media_id", required=True
    )
    media_type = fields.Selection(related="media_id.media_type")
    content_type = fields.Selection(
        related="post_id.content_type",
        store=True,
        readonly=False,
        help="Type of content - inherited from post but can be overridden per account",
    )

    state = fields.Selection(
        [
            ("ready", "Ready"),
            ("posting", "Posting"),
            ("posted", "Posted"),
            ("failed", "Failed"),
        ],
        default="ready",
    )
    published_date = fields.Datetime()
    published = fields.Boolean(default=True)
    message = fields.Text(required=True)

    comment_count = fields.Integer()
    like_count = fields.Integer()
    click_count = fields.Integer()
    share_count = fields.Integer()
    view_count = fields.Integer(string="Views", help="Number of views/impressions")
    impression_count = fields.Float()
    engagement = fields.Float()

    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_post_account_video_rel",
        column1="post_id",
        column2="video_id",
    )

    image_ids = fields.Many2many(
        "ir.attachment",
        relation="social_post_account_image_rel",
        column1="post_id",
        column2="image_id",
    )

    fb_video_url = fields.Char(
        string="Facebook Video URL",
        help=(
            "URL to display video in template. "
            "Generated from video_ids or synced from Facebook."
        ),
    )

    failed_description = fields.Html()
    post_account_url = fields.Char()
    author = fields.Char(related="account_id.name", store=True)
    actor_urn = fields.Char()

    def action_like_post(self, author_urn=None):
        return {"success": True, "message": ""}

    def action_like_comment(self, author_urn=None):
        return {"success": True, "message": ""}

    def _action_post(self):
        """
        Post on social network
        """
        pass

    def _action_campaign_post(self, post_id):
        pass

    def _delete_post_account(self):
        pass

    def delete_post_account(self):
        self._delete_post_account()
        account_id = self.account_id
        post_id = self.post_id
        self.unlink()
        if not post_id.post_account_ids:
            post_id.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Post deleted [%(account)s]") % {"account": account_id.name},
                "type": "success",
                "message": _("The post was successfully deleted."),
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

    def filter_by_media_types(self, media_types):
        return self.env["social.post.account"].search(
            [
                ("media_type", "in", media_types),
                ("state", "in", ("ready", "failed")),
            ]
        )

    def get_comments(self):
        return {"success": False, "data": []}

    def create_comment(self, post_data, context=None):
        pass
