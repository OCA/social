# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.osv import expression


class SocialPost(models.Model):
    """LinkedIn Ads constraints on the campaigns a post can promote."""

    _inherit = "social.post"

    def _get_allow_social_campaign_domain(self):
        """Only offer the LinkedIn campaigns this post can actually be sponsored by.

        A sponsored creative can only be attached to a campaign carrying a
        remote reference, so campaigns not created on LinkedIn yet are kept
        out of the selection. The ad format is filtered too, because LinkedIn
        refuses a creative whose content does not match the format chosen when
        the campaign was created: a post with a video needs a 'Single video'
        campaign and a post without one needs a 'Standard update' campaign.
        Campaigns without a format behave as standard ones, hence the ``!=``
        operator, which also matches them.

        :rtype: list
        """
        domain = super()._get_allow_social_campaign_domain()
        format_operator = "=" if self.video_ids else "!="
        return expression.AND(
            [
                domain,
                [
                    "|",
                    ("media_id.media_type", "!=", "linkedin"),
                    "&",
                    ("remote_ref", "!=", False),
                    ("linkedin_format", format_operator, "SINGLE_VIDEO"),
                ],
            ]
        )

    @api.depends("video_ids")
    def _compute_allow_social_campaign_ids(self):
        """Only declares the advertising dependencies of the computation."""
        return super()._compute_allow_social_campaign_ids()

    @api.depends(
        "social_campaign_id",
        "social_campaign_id.media_id",
        "social_campaign_id.campaign_group_id",
        "social_campaign_id.remote_ref",
        "social_campaign_id.linkedin_format",
    )
    def _compute_post_check_messages(self):
        """Only declares the advertising dependencies of the computation."""
        return super()._compute_post_check_messages()

    def _requires_campaign_post(self):
        """Return whether publishing this post must create a LinkedIn ad.

        The publication answers the same question about itself in
        :meth:`~odoo.addons.social_media_advertising_linkedin.models.
        social_post_account.SocialPostAccount._requires_campaign_post`. Here
        the social media is not read from the campaign of the publication but
        from the campaign of the post, which is where the user chooses it.

        :rtype: bool
        """
        self.ensure_one()
        return bool(
            self.social_campaign_id
            and self.social_campaign_id.campaign_group_id
            and self.social_campaign_id.media_id.media_type == "linkedin"
        )

    def _get_post_errors(self, media_type, account=None):
        """Add what stops LinkedIn from sponsoring this post.

        The sponsored creative is created after the post is online and its
        failure is only reported, so everything that can be known upfront is
        said here, while nothing irreversible has happened yet.

        The advertising account is the one rule of the three that belongs to
        the account and not to LinkedIn, so it is only answered when a
        publication asks: a post spread over two accounts, one of them
        without an advertising account, still publishes on the other.
        """
        errors = super()._get_post_errors(media_type, account=account)
        if media_type != "linkedin" or not self._requires_campaign_post():
            return errors
        campaign = self.social_campaign_id
        if not campaign.remote_ref:
            errors.append(
                _(
                    "The campaign %(campaign)s has not been created on "
                    "LinkedIn yet. Use the 'Create in LinkedIn' button on the "
                    "campaign before posting.",
                    campaign=campaign.display_name,
                )
            )
        errors += self._get_linkedin_campaign_format_errors()
        if account and not account._get_linkedin_ad_account_id():
            errors.append(
                _(
                    "No LinkedIn advertising account is in use for the account "
                    "%(account)s. Open its Advertising tab, fetch the "
                    "advertising accounts and choose one.",
                    account=account.display_name,
                )
            )
        return errors

    def _get_linkedin_campaign_format_errors(self):
        """Return what the ad format of the campaign refuses to sponsor.

        LinkedIn only accepts creatives of the format chosen when the
        campaign was created, and that format cannot be changed afterwards,
        so publishing a video in a standard campaign would leave the post
        online without its ad. A post carrying several images is published as
        a multi-image post, which LinkedIn does not sponsor at all.

        :rtype: list
        """
        self.ensure_one()
        campaign = self.social_campaign_id
        has_video = bool(self.video_ids)
        is_video_campaign = campaign.linkedin_format == "SINGLE_VIDEO"
        if not has_video and len(self.image_ids) > 1:
            return [
                _(
                    "LinkedIn does not sponsor posts with several images: they "
                    "are published as a multi-image post, a format its API "
                    "cannot turn into an ad, so this post cannot be linked to "
                    "the campaign %(campaign)s. Publish it with a single image "
                    "or without a campaign. LinkedIn offers the Carousel ad "
                    "format for this case, which this module does not support "
                    "yet.",
                    campaign=campaign.display_name,
                )
            ]
        if has_video and not is_video_campaign:
            return [
                _(
                    "LinkedIn only sponsors a post carrying a video through a "
                    "campaign of the 'Single video' format. The campaign "
                    "%(campaign)s uses 'Standard update', and LinkedIn does "
                    "not allow changing it once the campaign is created.",
                    campaign=campaign.display_name,
                )
            ]
        if is_video_campaign and not has_video:
            return [
                _(
                    "LinkedIn campaign %(campaign)s uses the 'Single video' "
                    "format, so it only accepts posts containing a video.",
                    campaign=campaign.display_name,
                )
            ]
        return []
