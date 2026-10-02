# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from ..social_advertising_linkedin_utils import _SCOPE_ADS_LINKEDIN


class SocialMedia(models.Model):
    _inherit = "social.media"

    def _get_linkedin_scopes(self):
        """Append the Advertising API scopes to the LinkedIn authorization.

        The tokens already issued keep the scopes they were granted with, so
        every account authorized before installing this module has to be
        re-authorized from the account wizard to be able to call the Ads API.
        """
        scopes = super()._get_linkedin_scopes()
        return scopes + [s for s in _SCOPE_ADS_LINKEDIN if s not in scopes]
