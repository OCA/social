# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import models


class SocialMediaBaseMixin(models.AbstractModel):
    _name = "social.media.base.mixin"
    _description = "Social Media Base Mixin"

    def _get_account_by_media(self):
        if self:
            return self.env["social.account"].search_count([("media_id", "=", self.id)])
        return None

    def _notify_user_client(
        self,
        target=None,
        notif_type=None,
        notif_message=None,
        media=False,
        social_name=False,
        account_name=False,
    ):
        """
        Notify the user of an event.

        :param target: The target of the notification.
                       If not provided, the current user will be notified.
        :param notif_type: The type of the notification.
                           If not provided, it will be set to "danger".
        :param notif_message: The message to be displayed to the user.
        :param media: If True, the notification will be about a social media.
        :param social_name: If True, the name of the social media will
                            be included in the notification.
        :param account_name: If True, the name of the account will
                            be included in the notification.
        """
        message_type = (
            notif_type.split("_")[-1] if len(notif_type.split("_")) > 0 else "danger"
        )
        message = ""
        if media:
            social_media_name = (
                media.upper() + " " + social_name if social_name else media.upper()
            )
            message = Markup(
                self.env._(
                    "Social Media %(social_media)s <b> "
                    "[%(account)s] </b> <br><br> %(message)s",
                    social_media=social_media_name,
                    account=social_media_name if not account_name else account_name,
                    message=f"<b>{'ERROR:' if message_type == 'danger' else ''}"
                    f"</b> {notif_message}",
                )
            )

        # Notifying the user
        if message:
            self.env["bus.bus"]._sendone(
                target or self.env.user.partner_id,
                notif_type,
                {
                    "message_type": message_type,
                    "message": message,
                },
            )
