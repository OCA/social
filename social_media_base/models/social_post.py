# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SocialPost(models.Model):
    _name = "social.post"
    _inherit = ["mail.thread", "mail.activity.mixin", "social.post.mixin"]
    _description = "Social Post"

    account_ids = fields.Many2many(
        "social.account", required=True, ondelete="restrict", string="Accounts"
    )
    active = fields.Boolean(default=True)
    content_type = fields.Selection(
        [
            ("post", "Post"),
            ("reel", "Video"),
            ("story", "Story"),
            ("ad", "Ad"),
        ],
        default="post",
        required=True,
        tracking=True,
        help=(
            "Type of content: Post, Video, Story, Ad. "
            "Platforms may support different types."
        ),
    )
    message = fields.Text(required=True, tracking=True)
    campaign_id = fields.Many2one("utm.campaign")
    send_post = fields.Selection(
        [("now", "Now"), ("schedule", "Schedule")],
        required=True,
        default="now",
        tracking=True,
    )
    send_post_date = fields.Datetime(
        string="Schedule date",
        # compute="_compute_send_post_date",
        store=True,
    )
    published_date = fields.Datetime(tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("publishing", "Publishing"),
            ("published", "Published"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )
    post_account_ids = fields.One2many("social.post.account", "post_id")

    count_post_likes = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Likes"
    )
    count_post_comments = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Comments"
    )
    count_post_clicks = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Clicks"
    )
    count_post_shares = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Shares"
    )
    count_post_impression = fields.Integer(
        compute="_compute_post_statistics", default=0, string="Impression"
    )
    count_post_engagement = fields.Float(
        compute="_compute_post_statistics", default=0, string="Engagement"
    )
    count_post_interactions = fields.Float(
        compute="_compute_post_statistics", default=0, string="Interactions"
    )

    image_ids = fields.Many2many(
        "ir.attachment",
        column1="post_id",
        column2="image_id",
        ondelete="restrict",
        relation="social_network_post_image_rel",
        string="Images",
        help=(
            "Attach multiple images (up to 10). "
            "Cannot mix images and videos in the same post."
        ),
    )

    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_network_post_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
        string="Videos",
        help="Attach a single video. Cannot mix images and videos in the same post. "
        "Note: Only the first video will be used for Facebook posts.",
    )

    post_preview = fields.Html(compute="_compute_post_preview", store=True)
    message_info = fields.Text(compute="_compute_message_info")
    any_failed_post = fields.Boolean(compute="_compute_any_failed_post")
    hide_post = fields.Boolean(compute="_compute_hide_post")

    # mail.activity.mixin - Override to add groups for cleaner prefetch
    activity_ids = fields.One2many(groups="base.group_user")
    activity_state = fields.Selection(groups="base.group_user")
    activity_user_id = fields.Many2one(groups="base.group_user")
    activity_type_id = fields.Many2one(groups="base.group_user")
    activity_type_icon = fields.Char(groups="base.group_user")
    activity_date_deadline = fields.Date(groups="base.group_user")
    my_activity_date_deadline = fields.Date(groups="base.group_user")
    activity_summary = fields.Char(groups="base.group_user")
    activity_exception_decoration = fields.Selection(groups="base.group_user")
    activity_exception_icon = fields.Char(groups="base.group_user")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("send_post", False) == "schedule":
                vals["state"] = "planned"
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        for post in self:
            if ("send_post" in vals and vals["send_post"] == "schedule") or (
                "send_post_date" in vals and post.send_post == "schedule"
            ):
                post.state = "planned"
        return res

    @api.depends("state", "any_failed_post", "send_post", "message", "account_ids")
    def _compute_hide_post(self):
        for post in self:
            post.hide_post = (
                (
                    post.state in ("planned", "publishing", "published", "cancelled")
                    and not post.any_failed_post
                )
                or not post.message
                or not post.account_ids
            )

    @api.depends("post_account_ids")
    def _compute_any_failed_post(self):
        for post in self:
            post.any_failed_post = any(
                post_account.state == "failed" for post_account in post.post_account_ids
            ) or (post.state == "publishing" and not post.post_account_ids)

    @api.depends("account_ids")
    def _compute_message_info(self):
        pass

    @api.depends("account_ids.media_id")
    def _compute_display_name(self):
        for acc in self:
            acc.display_name = "Post on {}".format(
                ", ".join(acc.account_ids.mapped("media_id.name"))
            )

    @api.depends("send_post")
    def _compute_send_post_date(self):
        for post in self:
            if post.send_post == "schedule":
                post.send_post_date = fields.Datetime.now() + timedelta(hours=1)
                post.state = "planned"

    @api.depends(
        "post_account_ids.like_count",
        "post_account_ids.comment_count",
        "post_account_ids.click_count",
        "post_account_ids.share_count",
        "post_account_ids.engagement",
        "post_account_ids.impression_count",
    )
    def _compute_post_statistics(self):
        for post in self:
            post.count_post_clicks = sum(post.mapped("post_account_ids.click_count"))
            post.count_post_shares = sum(post.mapped("post_account_ids.share_count"))
            post.count_post_likes = sum(post.mapped("post_account_ids.like_count"))
            post.count_post_engagement = sum(post.mapped("post_account_ids.engagement"))
            post.count_post_impression = sum(
                post.mapped("post_account_ids.impression_count")
            )
            post.count_post_comments = sum(
                post.mapped("post_account_ids.comment_count")
            )
            post.count_post_interactions = (
                post.count_post_clicks
                + post.count_post_likes
                + post.count_post_comments
                + post.count_post_shares
            )

    def filter_by_media_types(self, media_types, add_domain=None):
        domain = [
            ("media_type", "in", media_types),
            ("post_id", "=", self.id),
            ("state", "in", ("ready", "failed")),
        ]
        if add_domain:
            domain += add_domain
        return self.env["social.post.account"].search(domain)

    def action_draft(self):
        for post in self:
            post.state = "draft"

    def action_cancel(self):
        for post in self:
            if post.state in ("publishing", "published"):
                raise ValidationError(
                    self.env._(
                        "%(post)s: cannot be cancelled because it "
                        "is published or in the process of being published.",
                        post=post.display_name,
                    )
                )
            post.state = "cancelled"

    def _render_values_preview(self):
        """
        Add extra values dictionary for preview view, if necessary.
        """
        return {}

    def _render_template_preview(self):
        """
        Render the template for the preview view of the post.

        :return: A string containing the rendered templates.
        :rtype: str
        """
        render_template = ""
        IrQweb = self.env["ir.qweb"]
        for account in self.account_ids:
            values = {
                "media_id": account.media_id,
                "author": account.name,
                "message": self.message,
                "image_ids": self.image_ids[0:2],
            }
            try:
                render_template += """\n\n""" + IrQweb._render(
                    f"social_media_{account.media_id.media_type}.social_network_post_preview",
                    values | self._render_values_preview(),
                )
            except ValueError:
                render_template += """\n\n""" + IrQweb._render(
                    "social_media_base.social_network_post_preview",
                    values | self._render_values_preview(),
                )
        return (
            render_template if render_template else self.env._("No preview available")
        )

    @api.depends("account_ids", "message", "image_ids", "video_ids")
    def _compute_post_preview(self):
        """
        This method is responsible for obtaining the templates
        to preview the posts when they are created.

        Template ID format:
         * social_media_{media_type}.social_network_post_preview
        Example:
         * social_media_linkedin.social_network_post_preview

        As many templates as there are media according to the accounts selected in
        the post will be rendered.

        If the template does not exist, a default one is rendered.
        """
        for post in self:
            post.post_preview = post._render_template_preview()

    def _default_account_ids(self):
        """
        Returns a list of default account IDs to use when creating a post.
        By default, this method returns an empty list.

        :rtype: list[int]
        """
        return []

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        account_ids = self._default_account_ids()
        if account_ids:
            res["account_ids"] = [Command.set(account_ids)]
        return res

    def action_create_post_account(self):
        """
        Publishes the post on all the
        associated social media accounts.
        """
        self._action_create_post_account()

    def _prepare_post_account_values(self):
        """
        Prepare the posting values for each account.
        """
        posts_account = []
        for account in self.account_ids:
            fb_video_url = None
            if self.video_ids:
                first_video = self.video_ids[0]
                # Generate the URL for the video attachment
                fb_video_url = f"/web/image/{first_video._name}/{first_video.id}/datas"

            posts_account.append(
                Command.create(
                    {
                        "post_id": self.id,
                        "account_id": account.id,
                        "state": "ready",
                        "message": self.message,
                        "fb_video_url": fb_video_url,
                    }
                )
            )
        return posts_account

    def _action_create_post_account(self):
        """
        The posts are sent to social media.
        """
        SocialPostAccount = self.env["social.post.account"]
        for post in self:
            post.write(
                {
                    "state": "publishing",
                    "published_date": fields.Datetime.now(),
                    "post_account_ids": post._prepare_post_account_values(),
                }
            )
            SocialPostAccount._action_post(post_id=post)
            post.write(
                {
                    "state": "published",
                }
            )

    def _run_send_post(self):
        """
        Runs the scheduled posts.

        It looks for all the posts that are scheduled to be sent
        and sends them to social media.
        """
        post_accounts = self.env["social.post"].search(
            [
                ("state", "=", "planned"),
                ("send_post", "=", "schedule"),
                ("send_post_date", "<=", fields.Datetime.now()),
            ]
        )
        post_accounts._action_create_post_account()
