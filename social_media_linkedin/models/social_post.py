# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools

from odoo import _, models
from odoo.tools import human_size

from ..social_linkedin_utils import (
    _IMAGE_MIMETYPES_LINKEDIN,
    _MAX_IMAGE_SIZE_LINKEDIN,
    _MAX_IMAGES_LINKEDIN,
    _MAX_MESSAGE_LENGTH_LINKEDIN,
    _MAX_VIDEO_SIZE_LINKEDIN,
    _MAX_VIDEOS_LINKEDIN,
    _VIDEO_MIMETYPES_LINKEDIN,
)


class SocialPost(models.Model):
    """LinkedIn specific constraints on the posts to publish."""

    _inherit = "social.post"

    def _default_account_ids(self):
        """Preselect the LinkedIn accounts of the active company.

        The company is filtered in the domain on purpose: the record rule of
        ``social.account`` matches ``company_ids``, the companies the user is
        allowed to see, so without this an account of another activated
        company would be preselected as well.
        """
        res = super()._default_account_ids()
        account_ids = self.env["social.account"].search(
            [
                ("media_type", "=", "linkedin"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ]
        )
        if account_ids:
            return list(itertools.chain(account_ids.ids, res))
        return res

    def _render_values_preview(self, media):
        """Drop the images LinkedIn will not publish from its preview.

        The Posts API holds a single media entry, so a post carrying a video
        is published without its images (see
        :meth:`~odoo.addons.social_media_linkedin.models.social_account.
        SocialAccount._linkedin_create_post`). Showing them would preview
        exactly what does not reach LinkedIn. Only the LinkedIn preview is
        touched: another media of the same post may well publish them.
        """
        values = super()._render_values_preview(media)
        if media.media_type == "linkedin" and self.video_ids:
            values = dict(values, image_ids=self.env["ir.attachment"])
        return values

    def _get_post_errors(self, media_type, account=None):
        """Add what LinkedIn refuses to publish.

        With a video the images are not published at all (see
        :meth:`_render_values_preview`), so their number, their format and
        their size decide nothing and checking them would refuse a post
        LinkedIn takes just fine.
        """
        errors = super()._get_post_errors(media_type, account=account)
        if media_type != "linkedin":
            return errors
        if len(self.message or "") > _MAX_MESSAGE_LENGTH_LINKEDIN:
            errors.append(
                _(
                    "LinkedIn publishes at most %(limit)s characters per post, "
                    "and this one has %(length)s. Shorten the message to "
                    "publish it.",
                    limit=_MAX_MESSAGE_LENGTH_LINKEDIN,
                    length=len(self.message),
                )
            )
        if len(self.video_ids) > _MAX_VIDEOS_LINKEDIN:
            errors.append(
                _(
                    "LinkedIn publishes a single video per post, so this post "
                    "carrying %(videos)s videos cannot be published. Leave one "
                    "video or create a separate post for each of them.",
                    videos=len(self.video_ids),
                )
            )
        wrong_videos, large_videos = self._filter_linkedin_media(
            self.video_ids, _VIDEO_MIMETYPES_LINKEDIN, _MAX_VIDEO_SIZE_LINKEDIN
        )
        if wrong_videos:
            errors.append(
                _(
                    "LinkedIn only publishes MP4 videos, so %(names)s cannot "
                    "be published. Convert them to MP4 or remove them from the "
                    "post.",
                    names=", ".join(wrong_videos.mapped("name")),
                )
            )
        if large_videos:
            errors.append(
                _(
                    "LinkedIn publishes videos of at most %(limit)s, so "
                    "%(names)s cannot be published. Reduce their size or "
                    "remove them from the post.",
                    limit=human_size(_MAX_VIDEO_SIZE_LINKEDIN),
                    names=", ".join(large_videos.mapped("name")),
                )
            )
        if self.video_ids:
            return errors
        if len(self.image_ids) > _MAX_IMAGES_LINKEDIN:
            errors.append(
                _(
                    "LinkedIn publishes at most %(limit)s images per post, and "
                    "this one carries %(images)s. Remove some of them or "
                    "create a separate post.",
                    limit=_MAX_IMAGES_LINKEDIN,
                    images=len(self.image_ids),
                )
            )
        wrong_images, large_images = self._filter_linkedin_media(
            self.image_ids, _IMAGE_MIMETYPES_LINKEDIN, _MAX_IMAGE_SIZE_LINKEDIN
        )
        if wrong_images:
            errors.append(
                _(
                    "LinkedIn only publishes JPG, PNG and GIF images, so "
                    "%(names)s cannot be published. Convert them or remove "
                    "them from the post.",
                    names=", ".join(wrong_images.mapped("name")),
                )
            )
        if large_images:
            errors.append(
                _(
                    "LinkedIn publishes images of at most %(limit)s, so "
                    "%(names)s cannot be published. Reduce their size or "
                    "remove them from the post.",
                    limit=human_size(_MAX_IMAGE_SIZE_LINKEDIN),
                    names=", ".join(large_images.mapped("name")),
                )
            )
        return errors

    def _get_post_warnings(self, media_type, account=None):
        """Add what LinkedIn publishes differently from what the post says."""
        warnings = super()._get_post_warnings(media_type, account=account)
        if media_type != "linkedin":
            return warnings
        if self.image_ids and self.video_ids:
            warnings.append(
                _(
                    "LinkedIn does not combine images and a video in the same "
                    "post, so only the video will be published. Remove the "
                    "video to publish the images, or create a separate post "
                    "for them."
                )
            )
        return warnings

    def _filter_linkedin_media(self, attachments, mimetypes, max_size):
        """Split off the attachments LinkedIn will not take.

        The offenders are returned grouped and not one message per file: a
        post carrying ten images in the wrong format is one thing to fix, not
        ten lines to read.

        :param attachments: the ``ir.attachment`` records to check.
        :param mimetypes: the mimetypes LinkedIn publishes.
        :param int max_size: the size in bytes LinkedIn stops at.
        :return: the attachments in the wrong format, and the too large ones.
        :rtype: tuple
        """
        self.ensure_one()
        wrong_format = attachments.filtered(
            lambda attachment: (attachment.mimetype or "").lower() not in mimetypes
        )
        too_large = attachments.filtered(
            lambda attachment: attachment.file_size > max_size
        )
        return wrong_format, too_large
