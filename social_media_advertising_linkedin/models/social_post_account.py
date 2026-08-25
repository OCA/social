# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

import psycopg2

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_ERRORS_TO_RETRY

from ..social_advertising_linkedin_utils import _ENDPOINT_AD_CREATIVES_LINKEDIN

_logger = logging.getLogger(__name__)


class SocialPostAccount(models.Model):
    """Sponsored creative of a publication on a LinkedIn account."""

    _inherit = "social.post.account"

    creative_urn = fields.Char(
        string="Creative Reference",
        copy=False,
        help="URN of the sponsored creative of this publication on LinkedIn.",
    )

    def _requires_campaign_post(self):
        """Return whether publishing must create a LinkedIn sponsored creative.

        The campaign is read from ``social_campaign_id`` and not from the
        parent post, so publications imported from LinkedIn — which have no
        parent post — resolve it the same way.

        :rtype: bool
        """
        self.ensure_one()
        return bool(
            self.media_id.media_type == "linkedin"
            and self.social_campaign_id
            and self.social_campaign_id.campaign_group_id
            and self.social_campaign_id.media_id.media_type == "linkedin"
        )

    def _action_campaign_post(self, post_id):
        """Create the sponsored creative of the post on LinkedIn.

        :param post_id: URN of the post published on LinkedIn.
        :return: URN of the creative created on LinkedIn.
        """
        res = super()._action_campaign_post(post_id)
        if self._requires_campaign_post():
            campaign_linkedin_urn = self.social_campaign_id.remote_ref
            if not campaign_linkedin_urn:
                raise UserError(
                    _(
                        "The campaign %(campaign)s has not been created on "
                        "LinkedIn yet. Use the 'Create in LinkedIn' button "
                        "on the campaign before posting.",
                        campaign=self.social_campaign_id.display_name,
                    )
                )
            if not post_id:
                raise UserError(
                    _(
                        "The campaign could not be generated for the post, "
                        "please try again later."
                    )
                )
            ad_account_id = self.account_id._get_linkedin_ad_account_id()
            if not ad_account_id:
                raise UserError(
                    _(
                        "No LinkedIn advertising account is in use for "
                        "the account %(account)s. Open its "
                        "Advertising tab, fetch the advertising "
                        "accounts and choose one.",
                        account=self.account_id.display_name,
                    )
                )
            response = self.account_id._request_linkedin(
                method="POST",
                endpoint=_ENDPOINT_AD_CREATIVES_LINKEDIN % ad_account_id,
                headers=self.account_id.media_id._get_linkedin_headers(
                    self.account_id.sudo().access_token
                ),
                json_data={
                    "campaign": campaign_linkedin_urn,
                    "intendedStatus": "ACTIVE",
                    "content": {"reference": post_id},
                },
                return_json=False,
            )
            if response.status_code != 201:
                raise UserError(
                    _(
                        "The sponsored creative could not be created on "
                        "LinkedIn: %(error)s",
                        error=self.account_id._linkedin_error_message(response),
                    )
                )
            res = response.headers.get("x-restli-id")
        return res

    def _register_creative_failure(self, post_entity):
        """Log and report a creative that could not be created.

        The post itself is already online, so the failure is surfaced on the
        post chatter instead of being raised. Publications imported from
        LinkedIn have no parent post, hence the guard.

        :param post_entity: URN of the post published on LinkedIn.
        """
        _logger.exception(
            "Error creating the LinkedIn campaign creative for post %s",
            post_entity,
        )
        if self.post_id:
            self.post_id.message_post(
                body=_(
                    "The post was published on LinkedIn but the campaign "
                    "creative could not be created. Check the Ads permissions "
                    "of the account."
                )
            )

    def _linkedin_published_values(self, post_entity):
        """Store the URN of the sponsored creative of the post.

        This runs inside :meth:`_publish_guard` after ``remote_ref`` has been
        written, so no error may escape: rolling back the savepoint here would
        drop the reference of a post that already exists on LinkedIn, and
        retrying would publish it a second time. The only exception is the
        concurrency errors that :meth:`_publish_guard` re-raises on purpose:
        they must keep propagating so Odoo retries the whole transaction.

        :param post_entity: URN of the post published on LinkedIn.
        :rtype: dict
        """
        values = super()._linkedin_published_values(post_entity)
        if not self._requires_campaign_post():
            return values
        try:
            values["creative_urn"] = self._action_campaign_post(post_entity)
        except psycopg2.OperationalError as error:
            if error.pgcode in PG_CONCURRENCY_ERRORS_TO_RETRY:
                raise
            self._register_creative_failure(post_entity)
        except Exception:  # noqa: BLE001 - the post is already published
            self._register_creative_failure(post_entity)
        return values
