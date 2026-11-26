# Copyright 2026 Domatix <https://www.domatix.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .social_account import (
    _MAX_CAPTION_LENGTH_INSTAGRAM,
    _MAX_IMAGE_SIZE_INSTAGRAM,
    _MAX_IMAGES_INSTAGRAM,
)


class SocialPost(models.Model):
    """Instagram requirements on the posts to publish."""

    _inherit = "social.post"

    def _get_post_errors(self, media_type, account=None):
        """Instagram's limits, checked before the container is created."""
        errors = super()._get_post_errors(media_type, account=account)
        if media_type != "instagram":
            return errors
        message = self._get_checked_message()
        if len(message) > _MAX_CAPTION_LENGTH_INSTAGRAM:
            errors.append(
                self.env._(
                    "Instagram publishes at most %(limit)s characters per post, "
                    "and this one has %(length)s.",
                    limit=_MAX_CAPTION_LENGTH_INSTAGRAM,
                    length=len(message),
                )
            )
        if not self.image_ids and not self.video_ids:
            errors.append(
                self.env._(
                    "At least one image or a video is required when posting on "
                    "Instagram."
                )
            )
        if len(self.image_ids) > _MAX_IMAGES_INSTAGRAM:
            errors.append(
                self.env._(
                    "Instagram publishes at most %(limit)s images in a carousel, "
                    "and this post has %(count)s.",
                    limit=_MAX_IMAGES_INSTAGRAM,
                    count=len(self.image_ids),
                )
            )
        for image in self.image_ids:
            if image.mimetype not in ("image/jpeg", "image/jpg"):
                errors.append(
                    self.env._(
                        "%(image)s is not a JPEG image: Instagram only publishes "
                        "JPEG images.",
                        image=image.name,
                    )
                )
            elif image.file_size > _MAX_IMAGE_SIZE_INSTAGRAM:
                errors.append(
                    self.env._(
                        "%(image)s is larger than %(limit)s MB: Instagram does "
                        "not accept it.",
                        image=image.name,
                        limit=_MAX_IMAGE_SIZE_INSTAGRAM // (1024 * 1024),
                    )
                )
        return errors
