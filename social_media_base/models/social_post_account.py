# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

import requests

from odoo import Command, fields, models


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

    def _action_post(self, post_id):
        """
        Post on social network
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
                "title": self.env._(
                    "Post deleted [%(account)s]", account=account_id.name
                ),
                "type": "success",
                "message": self.env._("The post was successfully deleted."),
                "next": {"type": "ir.actions.client", "tag": "reload"},
            },
        }

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

    def _get_medias_account(self, medias):
        return (
            self.env["ir.attachment"]
            .search(
                [
                    ("name", "in", medias),
                ]
            )
            .mapped("name")
        )

    def _map_medias_account(self, **values):
        attach_values = values or {}
        media_content = (
            requests.get(values["url"], timeout=10)
            if values.get("url", False)
            else None
        )
        if media_content and media_content.status_code == 200:
            attach_values.update(
                {
                    "type": "binary",
                    "res_model": self._name,
                    "res_id": self.id,
                    "datas": base64.b64encode(media_content.content),
                }
            )
        return Command.create(attach_values)