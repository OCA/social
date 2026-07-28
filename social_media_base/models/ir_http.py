# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        """Deliver once the notification kept by the social media callbacks.

        See ``social.media.base.mixin._notify_user_session``.
        """
        result = super().session_info()
        notification = request.session.pop("social_media_notification", None)
        if notification:
            result["social_media_notification"] = notification
        return result
