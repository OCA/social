# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

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
        """Preselect the X accounts of the active company.

        The company is filtered in the domain on purpose: the record rule of
        ``social.account`` matches ``company_ids``, the companies the user is
        allowed to see, so without this an account of another activated
        company would be preselected as well.
        """
        res = super()._default_account_ids()
        account_ids = self.env["social.account"].search(
            [
                ("media_type", "=", "x"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ]
        )
        if account_ids:
            return list(itertools.chain(account_ids.ids, res))
        return res

    @api.constrains("account_ids", "message", "image_ids", "video_ids")
    def _check_account_ids(self):
        """Reject posts sent twice to the same X user, which X reads as spam."""
        for post in self:
            for username, count in post.account_ids._get_group_account_username():
                if count > 1:
                    raise ValidationError(
                        _(
                            "There are X accounts with the same username "
                            "(%(username)s), please check to avoid spam errors.",
                            username=username,
                        )
                    )

    def _get_post_errors(self, media_type, account=None):
        """Add what X refuses to publish.

        Unlike LinkedIn, which publishes the video of a post carrying both
        and drops the images, X takes one kind of media or the other, so a
        post mixing them is refused instead of warned about.
        """
        errors = super()._get_post_errors(media_type, account=account)
        if media_type != "x":
            return errors
        if len(self.message or "") > _MAX_MESSAGE_LENGTH_X:
            errors.append(
                _(
                    "X publishes at most %(limit)s characters per post, and "
                    "this one has %(length)s. Shorten the message to publish "
                    "it.",
                    limit=_MAX_MESSAGE_LENGTH_X,
                    length=len(self.message),
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
