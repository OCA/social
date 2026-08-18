# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

import requests

from odoo import Command, api, fields, models


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
    campaign_id = fields.Many2one(related="post_id.campaign_id")
    user_id = fields.Many2one(
        related="account_id.user_id",
        string="Responsible",
        store=True,
        index=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("ready", "Ready"),
            ("posted", "Posted"),
            ("failed", "Failed"),
            ("deleted", "Deleted"),
        ],
        default="ready",
        help="'Deleted' means the publication no longer exists on the "
        "social network although it is kept in Odoo for history.",
    )
    published_date = fields.Datetime()
    published = fields.Boolean(default=True)
    message = fields.Text(required=True)
    remote_ref = fields.Char(
        string="Remote Reference",
        copy=False,
        index=True,
        help="Identifier of this publication on the social network. It is set "
        "by the connector module of each social media.",
    )
    account_remote_ref = fields.Char(
        related="account_id.remote_ref", string="Account Remote Reference"
    )

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
    has_video = fields.Boolean(
        default=False,
        help="Indicates that the published post has at least one video attached.",
    )
    failed_description = fields.Html()
    post_account_url = fields.Char()
    author = fields.Char(related="account_id.name", store=True)
    actor_urn = fields.Char()

    def action_like_post(self, author_urn=None):
        """Like the publication on the social network.

        :param author_urn: actor urn performing the like.
        :return: ``success`` and ``message`` of the action.
        :rtype: dict
        """
        return {"success": True, "message": ""}

    def action_like_comment(self, author_urn=None):
        return {"success": True, "message": ""}

    def _action_post(self, post_id):
        """Publish on the social network, implemented by each connector.

        :param post_id: the ``social.post`` being published.
        """

    def _action_campaign_post(self, post_id):
        """Publish the campaign post on the social network.

        :param post_id: the ``social.post`` being published.
        :return: ``success`` and ``message`` of the action.
        :rtype: dict
        """

    def _delete_post_account(self):
        """Delete the publication on the social network.

        :return: ``success`` and ``message`` of the action.
        :rtype: dict
        """

    def delete_post_account(self):
        self.ensure_one()
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
        """Retrieve the comments of the publication.

        :return: ``success`` and ``data`` of the action.
        :rtype: dict
        """
        return {"success": False, "data": []}

    def create_comment(self, post_data, context=None):
        """Create a comment on the social network.

        :param post_data: message and other data of the comment.
        :param context: optional context used to render the comment.
        :return: ``success`` and ``data`` of the action.
        :rtype: dict
        """

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._anchor_media_attachments()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "image_ids" in vals or "video_ids" in vals:
            self._anchor_media_attachments()
        return res

    def _anchor_media_attachments(self):
        """Attach the downloaded medias to their publication.

        They are created together with it, so they end up with an empty
        ``res_id``: in that state only the administrators can read them and
        everybody else gets a placeholder instead of the image.
        """
        for post_account in self:
            attachments = (post_account.image_ids | post_account.video_ids).filtered(
                lambda attachment: not attachment.res_id
            )
            if attachments:
                attachments.sudo().write(
                    {"res_model": post_account._name, "res_id": post_account.id}
                )

    def _get_medias_account(self, medias):
        """Return the names of the medias already downloaded for this account.

        ``sudo()`` is needed to avoid downloading a media twice: a user who
        cannot read another user's attachments would otherwise duplicate
        every image on each synchronization.

        :rtype: list
        """
        if not medias:
            return []
        return (
            self.env["ir.attachment"]
            .sudo()
            .search(
                [
                    ("name", "in", medias),
                    ("res_model", "=", self._name),
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
