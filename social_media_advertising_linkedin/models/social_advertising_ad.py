# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from urllib.parse import quote

from odoo import _, api, models
from odoo.exceptions import UserError

from ..social_advertising_linkedin_utils import _ENDPOINT_AD_CREATIVES_LINKEDIN
from .social_advertising_campaign import LINKEDIN_LOCKED_CODES

_logger = logging.getLogger(__name__)

LINKEDIN_DELETABLE_CODE = "DRAFT"
LINKEDIN_PENDING_DELETION_CODE = "PENDING_DELETION"
LINKEDIN_REMOVED_CODE = "REMOVED"


class SocialAdvertisingAd(models.Model):
    """Deletion of an ad on LinkedIn."""

    _inherit = "social.advertising.ad"

    @api.depends("media_type", "remote_ref", "stage_id.code")
    def _compute_can_delete_remote_ad(self):
        """LinkedIn only deletes a creative it still accepts changes on.

        A creative that is archived, canceled or already on its way out is
        refused with ``Cannot update a canceled creative``, so the button is
        not offered: the same statuses that lock a campaign lock an ad.
        """
        res = super()._compute_can_delete_remote_ad()
        for ad in self.filtered(lambda ad: ad.media_type == "linkedin"):
            ad.can_delete_remote_ad = bool(
                ad.remote_ref and ad.stage_id.code not in LINKEDIN_LOCKED_CODES
            )
        return res

    def _register_remote_ad_gone(self):
        """Leave the LinkedIn status of an ad that stopped being answered.

        A creative LinkedIn does not return anymore is gone from it, so the
        status it was last fetched with, usually the pending deletion it was
        moved to, describes nothing. The stage is left missing rather than
        raised over: the synchronization of the other ads must not stop
        because a stage record is not installed.
        """
        super()._register_remote_ad_gone()
        linkedin_ads = self.filtered(lambda ad: ad.media_type == "linkedin")
        if not linkedin_ads:
            return
        stage = self.env["social.stage"]._get_stage(
            "linkedin", "ad", LINKEDIN_REMOVED_CODE
        )
        if stage:
            linkedin_ads.write({"stage_id": stage.id})

    def _delete_remote_ad(self):
        """Delete this ad on LinkedIn, or ask LinkedIn to delete it.

        The Creatives API only deletes a creative outright when it is still
        a draft, when its campaign is, or when it is a video that failed to
        process. Anything already served is not deleted on the spot: the
        deletion is requested by moving the creative to ``PENDING_DELETION``
        and LinkedIn processes it afterwards.

        Both cases go through the same button, so the deletable ones are
        tried first and the answer of LinkedIn decides: a creative Odoo
        believes deletable may not be one, and finding out costs the call
        that was going to be made anyway.

        A requested deletion is not taken at its word either. LinkedIn drops
        a creative right away when it has no performance data to keep, so
        the creative is read back: what it answers is what the user is told
        and what the status of the ad is set from, instead of a pending
        deletion that may already be done.
        """
        media_type = self.media_type
        if media_type != "linkedin":
            return super()._delete_remote_ad()
        account = self.account_id
        account._check_linkedin_scopes(["rw_ads"])
        endpoint = self._linkedin_creative_endpoint()
        if self._linkedin_is_deletable() and self._linkedin_delete_creative(endpoint):
            message = _("The ad was deleted on LinkedIn.")
            self.sudo().unlink()
            return self._notify_remote_ad_deleted(
                message, gone=True, media_type=media_type
            )
        self._linkedin_request_creative_deletion(endpoint)
        status = self._linkedin_read_creative_status(endpoint)
        self._linkedin_apply_deletion_status(status)
        if status:
            return self._notify_remote_ad_deleted(
                _(
                    "LinkedIn does not delete an ad that is being served "
                    "right away. The deletion was requested and is now "
                    "pending: the ad disappears once LinkedIn processes it."
                ),
                gone=False,
            )
        return self._notify_remote_ad_deleted(
            _(
                "The ad was deleted on LinkedIn. It is kept here as history, "
                "archived and with its statistics."
            ),
            gone=False,
        )

    @api.model
    def _advertising_ad_action(self, media_type=None):
        """Open the LinkedIn ads instead of the ads of every social media."""
        if media_type == "linkedin":
            return self.env["ir.actions.act_window"]._for_xml_id(
                "social_media_advertising_linkedin.social_advertising_ad_linkedin_action"
            )
        return super()._advertising_ad_action(media_type=media_type)

    def _linkedin_creative_endpoint(self):
        """Return the Creatives API endpoint of this ad.

        The advertising account is the one of the ad and not the one in use:
        an ad fetched before choosing another advertising account still
        belongs to the one it was served from.

        :rtype: str
        """
        ad_account_urn = self.advertising_account_id.remote_ref
        ad_account_id = (
            ad_account_urn.split(":")[-1]
            if ad_account_urn
            else self.account_id._require_linkedin_ad_account_id()
        )
        return (
            f"{_ENDPOINT_AD_CREATIVES_LINKEDIN % ad_account_id}/"
            f"{quote(self.remote_ref, safe='')}"
        )

    def _linkedin_is_deletable(self):
        """Whether LinkedIn may delete this creative outright.

        The state of the video is not stored, so a video that failed to
        process is not recognised here: it simply goes through the answer of
        LinkedIn like any other creative.

        :rtype: bool
        """
        return LINKEDIN_DELETABLE_CODE in (
            self.stage_id.code,
            self.campaign_id.stage_id.code,
        )

    def _linkedin_delete_creative(self, endpoint):
        """Ask LinkedIn to delete the creative outright.

        A refusal is not an error: it means the creative has to go through
        the pending deletion instead, which is what the caller does next.

        :param endpoint: the Creatives API endpoint of this ad.
        :return: whether LinkedIn deleted it.
        :rtype: bool
        """
        account = self.account_id
        response = account._request_linkedin(
            method="DELETE",
            endpoint=endpoint,
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                x_restli_method="DELETE",
            ),
            return_json=False,
        )
        if response.status_code == 204:
            return True
        _logger.info(
            "LinkedIn refused to delete the creative %(creative)s outright, "
            "its deletion is requested instead: %(error)s",
            {
                "creative": self.remote_ref,
                "error": account._linkedin_error_message(response),
            },
        )
        return False

    def _linkedin_request_creative_deletion(self, endpoint):
        """Ask LinkedIn to delete the creative.

        :param endpoint: the Creatives API endpoint of this ad.
        """
        account = self.account_id
        response = account._request_linkedin(
            method="POST",
            endpoint=endpoint,
            headers=account.media_id._get_linkedin_headers(
                account.sudo().access_token,
                content_type="application/json",
                x_restli_method="PARTIAL_UPDATE",
            ),
            json_data={
                "patch": {"$set": {"intendedStatus": LINKEDIN_PENDING_DELETION_CODE}}
            },
            return_json=False,
        )
        if response.status_code not in (200, 204):
            raise UserError(
                _(
                    "Error deleting the LinkedIn ad: %(error)s",
                    error=account._linkedin_error_message(response),
                )
            )

    def _linkedin_read_creative_status(self, endpoint):
        """Return the status LinkedIn reports for the creative, if any.

        A creative with nothing to keep is dropped as soon as its deletion
        is requested, and LinkedIn answers ``404`` from then on. Anything
        else is still there and answers the status it now holds.

        :param endpoint: the Creatives API endpoint of this ad.
        :return: the ``intendedStatus`` of the creative, or an empty string
            when LinkedIn does not know it anymore.
        :rtype: str
        """
        account = self.account_id
        response = account._request_linkedin(
            endpoint=endpoint,
            headers=account.media_id._get_linkedin_headers(account.sudo().access_token),
            return_json=False,
        )
        if response.status_code != 200:
            return ""
        return response.json().get("intendedStatus") or ""

    def _linkedin_apply_deletion_status(self, status):
        """Record on the ad what LinkedIn answered after the deletion.

        A creative LinkedIn no longer knows is archived, like the
        synchronization does with the ads that stop being answered: its
        statistics are the only trace left of what it did.

        :param status: the ``intendedStatus`` of the creative, empty when it
            is gone from LinkedIn.
        """
        code = status or LINKEDIN_REMOVED_CODE
        stage = self.env["social.stage"]._require_linkedin_stage("ad", code)
        values = {"stage_id": stage.id}
        if not status:
            values["active"] = False
        self.sudo().write(values)
