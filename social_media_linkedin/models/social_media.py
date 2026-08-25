# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models

from ..social_linkedin_utils import _HEADERS_LINKEDIN, _SCOPE_LINKEDIN


class SocialMedia(models.Model):
    """Registers LinkedIn as an available social media."""

    _inherit = "social.media"

    media_type = fields.Selection(selection_add=[("linkedin", "LinkedIn")])

    def _get_linkedin_headers(
        self, access_token=None, content_type=None, x_restli_method=None
    ):
        """Return the headers of a LinkedIn request.

        The common ones are always sent; the rest are added only when the
        call needs them, since LinkedIn refuses a request carrying a header
        that does not belong to it.

        :param access_token: the token authorizing the call, when it needs one.
        :param content_type: the media type of the body, when there is one.
        :param x_restli_method: the Rest.li method, for the endpoints that
            answer several entities at once.
        :rtype: dict
        """
        headers = _HEADERS_LINKEDIN.copy()
        if x_restli_method:
            headers.update({"X-RestLi-Method": x_restli_method})
        if access_token:
            headers.update({"Authorization": f"Bearer {access_token}"})
        if content_type:
            headers.update({"Content-Type": content_type})
        return headers

    def _get_linkedin_scopes(self):
        """Return the OAuth scopes requested when authorizing an account.

        Extension point: modules adding LinkedIn features append the scopes
        their API calls need.
        """
        self.ensure_one()
        return list(_SCOPE_LINKEDIN)

    def _get_utm_medium(self):
        """LinkedIn publications are reported under the LinkedIn medium.

        The medium is resolved here instead of in a data file: the social
        media of the connector already exists, so a ``noupdate`` record would
        never be applied and an updatable one would reset the medium chosen by
        the integrator on every module update.
        """
        self.ensure_one()
        if not self.utm_medium_id and self.media_type == "linkedin":
            return (
                self.env.ref("utm.utm_medium_linkedin", raise_if_not_found=False)
                or super()._get_utm_medium()
            )
        return super()._get_utm_medium()

    def action_open_account(self):
        """Open the wizard associating a LinkedIn account.

        No ``ensure_one`` here: every connector overrides this method and
        chains to the next one, so an empty recordset has to travel down to
        the hook of the base module instead of being refused on the way.
        Reading ``media_type`` already refuses a recordset of several media.

        :rtype: dict
        """
        res = super().action_open_account()
        if self.media_type == "linkedin":
            return {
                "res_model": "wizard.social.account",
                "views": [[False, "form"]],
                "target": "new",
                "type": "ir.actions.act_window",
                "context": {
                    "default_media_id": self.id,
                },
            }
        return res
