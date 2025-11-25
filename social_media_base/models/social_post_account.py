# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SocialPostAccount(models.Model):
    _name = "social.post.account"
    _inherit = ["mail.thread", "social.post.mixin"]
    _description = "Social Post Account"
    _rec_name = "message"

    post_id = fields.Many2one("social.post", ondelete="restrict")
    active = fields.Boolean(default=True)
    account_id = fields.Many2one("social.account", ondelete="restrict", required=True)
    media_id = fields.Many2one(
        "social.media", related="account_id.media_id", required=True
    )
    media_type = fields.Selection(related="media_id.media_type")

    state = fields.Selection(
        [
            ("ready", "Ready"),
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
    impression_count = fields.Float()
    engagement = fields.Float()

    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_post_account_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
    )

    image_ids = fields.Many2many(
        "ir.attachment",
        column1="post_id",
        column2="image_id",
        ondelete="restrict",
        relation="social_post_account_image_rel",
    )
    failed_description = fields.Html()
    post_account_url = fields.Char()
    author = fields.Char(related="account_id.name", store=True)
    actor_urn = fields.Char()

    def action_like_post(self, author_urn=None):
        """
        Likes the post on social media.

        :param author_urn: The actor urn of the user who is performing the like action.
        :type author_urn: str
        :return: A dictionary containing the success and message of the like action.
        :rtype: dict
        """
        return {"success": True, "message": ""}

    def action_like_comment(self, author_urn=None):
        return {"success": True, "message": ""}

    def _action_post(self):
        """
        Post on social media
        """
        pass

    def _action_campaign_post(self, post_id):
        """
        Publishes the campaign post on social media.

        :param post_id: The post ID of the campaign.
        :type post_id: int
        :return: A dictionary containing the success and message of the post action.
        :rtype: dict
        """
        pass

    def _delete_post_account(self):
        """
        Deletes the post account from social media.

        It should be overridden in the child classes to provide
        the specific implementation for each social media platform.

        :return: A dictionary containing the success and message of the deletion action.
        :rtype: dict
        """
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
                "title": self.env._("Post deleted [%(account)s]")
                % {"account": account_id.name},
                "type": "success",
                "message": self.env._("The post was successfully deleted."),
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
        """
        Retrieves the comments of the post on social media.

        :return: A dictionary containing the success and data of the comments action.
        :rtype: dict
        """
        return {"success": False, "data": []}

    def create_comment(self, post_data, context=None):
        """
        Creates a comment on social media.

        :param post_data: A dictionary containing the message and other post data.
        :type post_data: dict
        :param context: Optional context to use for rendering the comment.
        :type context: dict
        :return: A dictionary containing the success and data of the comment action.
        :rtype: dict
        """
        pass
