# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SocialPost(models.Model):
    _name = "social.post"
    _inherit = ["mail.thread", "mail.activity.mixin", "social.post.mixin"]
    _description = "Social Post"

    account_ids = fields.Many2many("social.account", required=True, ondelete="restrict")
    active = fields.Boolean(default=True)
    message = fields.Text(required=True, tracking=True)
    campaign_id = fields.Many2one("utm.campaign")
    send_post = fields.Selection(
        [("now", "Now"), ("schedule", "Schedule")],
        required=True,
        default="now",
        tracking=True,
    )
    send_post_date = fields.Datetime(
        string="Schedule date", compute="_compute_send_post_date", store=True
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
    )

    video_ids = fields.Many2many(
        "ir.attachment",
        relation="social_network_post_video_rel",
        column1="post_id",
        column2="video_id",
        ondelete="restrict",
    )

    post_preview = fields.Html(compute="_compute_post_preview", store=True)

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
                post.send_post_date = datetime.now() + timedelta(hours=1)
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
            post.count_post_impression = sum(post.mapped("post_account_ids.engagement"))
            post.count_post_comments = sum(
                post.mapped("post_account_ids.comment_count")
            )
            post.count_post_interactions = (
                post.count_post_clicks
                + post.count_post_likes
                + post.count_post_comments
                + post.count_post_shares
            )

    def action_draft(self):
        for post in self:
            post.state = "draft"

    def action_cancel(self):
        for post in self:
            if post.state in ("publishing", "published"):
                raise ValidationError(
                    _(
                        "%(post)s: cannot be cancelled because it "
                        "is published or in the process of being published."
                    )
                    % {"post": post.display_name}
                )
            post.state = "cancelled"

    def _render_values_preview(self):
        """
         Add extra values dictionary for preview view, if necessary.
        :rtype: dict
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
                    f"social_media_{account.media_id.media_type}.social_media_post_preview",
                    values | self._render_values_preview(),
                )
            except ValueError:
                render_template += """\n\n""" + IrQweb._render(
                    "social_media_base.social_media_post_preview",
                    values | self._render_values_preview(),
                )
        return render_template if render_template else _("No preview available")

    @api.depends("account_ids", "message", "image_ids", "video_ids")
    def _compute_post_preview(self):
        """
        This method is responsible for obtaining the templates
        to preview the posts when they are created.

        Template ID format:
         * social_media_{media_type}.social_media_post_preview
        Example:
         * social_media_linkedin.social_media_post_preview

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
            res["account_ids"] = [(6, 0, account_ids)]
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
            if account.id not in self.post_account_ids.mapped("account_id").ids:
                posts_account.append(
                    Command.create(
                        {
                            "post_id": self.id,
                            "account_id": account.id,
                            "state": "ready",
                            "message": self.message,
                        }
                    )
                )
        return posts_account

    def _action_create_post_account(self):
        """
        The posts are sent to social media.
        """
        for post in self:
            post.write(
                {
                    "state": "publishing",
                    "post_account_ids": post._prepare_post_account_values(),
                }
            )
            post.post_account_ids[0]._action_post()
            all_posted = all(
                post_acc.state == "posted" for post_acc in post.post_account_ids
            )
            if all_posted:
                post.write({"state": "published"})

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
                ("send_post_date", "<=", datetime.now()),
            ]
        )
        post_accounts.with_context(
            **{
                "social_post_cron": True,
            }
        )._action_create_post_account()
