# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import human_size

from ..social_x_utils import (
    _IMAGE_MIMETYPES_X,
    _MAX_GIF_SIZE_X,
    _MAX_IMAGE_SIZE_X,
    _MAX_IMAGES_X,
    _MAX_MESSAGE_LENGTH_X,
    _MAX_VIDEO_SIZE_X,
    _MAX_VIDEOS_X,
    _VIDEO_MIMETYPES_X,
)


class SocialPost(models.Model):
    """X specific defaults and constraints on the posts to publish."""

    _inherit = "social.post"

    def _default_account_ids(self):
        """Preselect the X accounts of the active company."""
        return self._default_account_ids_for_media("x") + super()._default_account_ids()

    @api.constrains("account_ids")
    def _check_account_ids(self):
        """Reject posts sent twice to the same X user, which X reads as spam.

        Only the accounts of the post decide the answer, so they are the only
        trigger: the duplicate appears when the selection changes, not when
        the content does.
        """
        for post in self:
            duplicates = post.account_ids._get_group_account_username()
            if duplicates:
                raise ValidationError(
                    _(
                        "There are X accounts with the same username "
                        "(%(username)s), please check to avoid spam errors.",
                        username=duplicates[0][0],
                    )
                )

    @api.depends("account_ids.x_premium")
    def _compute_post_check_messages(self):
        """Only declares that the plan of an account moves what X refuses."""
        return super()._compute_post_check_messages()

    def _get_post_errors(self, media_type, account=None):
        """Add what X refuses to publish.

        Unlike LinkedIn, which publishes the video of a post carrying both
        and drops the images, X takes one kind of media or the other, so a
        post mixing them is refused instead of warned about.

        The characters counted are the ones of
        :meth:`~odoo.addons.social_media_base.models.social_post.SocialPost.
        _get_checked_message`, so the limit of X is measured against the text
        the publication is about to send and not against an earlier version of
        it.

        How many they may be belongs to the account and not to X: Premium
        raises them from 280 to 25 000. The publication asks with its own
        account and is measured against its own limit; the form asks without
        one and is measured against the strictest of the X accounts of the
        post, which is the line that would fail.
        """
        errors = super()._get_post_errors(media_type, account=account)
        if media_type != "x":
            return errors
        message = self._get_checked_message()
        x_accounts = account or self.account_ids.filtered(
            lambda one: one.media_type == "x"
        )
        limit = (
            min(one._get_x_max_message_length() for one in x_accounts)
            if x_accounts
            else _MAX_MESSAGE_LENGTH_X
        )
        if len(message) > limit:
            errors.append(
                _(
                    "X publishes at most %(limit)s characters per post, and "
                    "this one has %(length)s. Shorten the message to publish "
                    "it.",
                    limit=limit,
                    length=len(message),
                )
            )
        if self.image_ids and self.video_ids:
            errors.append(
                _(
                    "X publishes either images or a video, not both in the "
                    "same post. Leave one kind of media or create a separate "
                    "post for each of them."
                )
            )
        if len(self.image_ids) > _MAX_IMAGES_X:
            errors.append(
                _(
                    "X publishes at most %(limit)s images per post, and this "
                    "one carries %(images)s. Remove some of them or create a "
                    "separate post.",
                    limit=_MAX_IMAGES_X,
                    images=len(self.image_ids),
                )
            )
        if len(self.video_ids) > _MAX_VIDEOS_X:
            errors.append(
                _(
                    "X publishes a single video per post, so this post "
                    "carrying %(videos)s videos cannot be published. Leave one "
                    "video or create a separate post for each of them.",
                    videos=len(self.video_ids),
                )
            )
        wrong_images = self.image_ids.filtered(
            lambda image: (image.mimetype or "").lower() not in _IMAGE_MIMETYPES_X
        )
        if wrong_images:
            errors.append(
                _(
                    "X only publishes JPG, PNG, WEBP and GIF images, so "
                    "%(names)s cannot be published. Convert them or remove "
                    "them from the post.",
                    names=", ".join(wrong_images.mapped("name")),
                )
            )
        large_images = self.image_ids.filtered(
            lambda image: image.file_size > self._get_x_image_size_limit(image)
        )
        if large_images:
            errors.append(
                _(
                    "X publishes images of at most %(limit)s, %(gif_limit)s "
                    "for a GIF, so %(names)s cannot be published. Reduce their "
                    "size or remove them from the post.",
                    limit=human_size(_MAX_IMAGE_SIZE_X),
                    gif_limit=human_size(_MAX_GIF_SIZE_X),
                    names=", ".join(large_images.mapped("name")),
                )
            )
        wrong_videos = self.video_ids.filtered(
            lambda video: (video.mimetype or "").lower() not in _VIDEO_MIMETYPES_X
        )
        if wrong_videos:
            errors.append(
                _(
                    "X only publishes MP4 videos, so %(names)s cannot be "
                    "published. Convert them to MP4 or remove them from the "
                    "post.",
                    names=", ".join(wrong_videos.mapped("name")),
                )
            )
        large_videos = self.video_ids.filtered(
            lambda video: video.file_size > _MAX_VIDEO_SIZE_X
        )
        if large_videos:
            errors.append(
                _(
                    "X publishes videos of at most %(limit)s, so %(names)s "
                    "cannot be published. Reduce their size or remove them "
                    "from the post.",
                    limit=human_size(_MAX_VIDEO_SIZE_X),
                    names=", ".join(large_videos.mapped("name")),
                )
            )
        return errors

    def _get_x_image_size_limit(self, image):
        """Return the size X stops at for one image.

        An animated GIF travels through the same upload as a still image but
        carries its own, larger limit, so the two cannot be checked against a
        single number.

        :param image: the ``ir.attachment`` to weigh.
        :rtype: int
        """
        if (image.mimetype or "").lower() == "image/gif":
            return _MAX_GIF_SIZE_X
        return _MAX_IMAGE_SIZE_X
