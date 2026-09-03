# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class UtmMedium(models.Model):
    _inherit = "utm.medium"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_social_media(self):
        """Keep the fallback medium of the publications alive."""
        utm_medium_social_media = self.env.ref(
            "social_media_base.utm_medium_social_media",
            raise_if_not_found=False,
        )
        if utm_medium_social_media and utm_medium_social_media in self:
            raise UserError(
                _(
                    "The UTM medium '%s' cannot be deleted as it is the one "
                    "reported for the publications of a social media that "
                    "declares no medium of its own.",
                    utm_medium_social_media.name,
                )
            )
