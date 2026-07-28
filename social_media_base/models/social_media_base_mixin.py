# Copyright 2025 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup, escape

from odoo import _, models
from odoo.http import request


class SocialMediaBaseMixin(models.AbstractModel):
    _name = "social.media.base.mixin"
    _description = "Social Media Base Mixin"

    def _notify_user_session(self, notif_message, message_type="danger"):
        """Keep a message in the session until the web client is loaded again.

        The OAuth callbacks answer with a redirect, so a message sent
        through the bus at that moment never reaches the user. These ones
        are delivered by ``ir.http.session_info`` instead.

        The message is rendered as markup by the web client, so only the
        messages built as ``Markup`` keep their tags: anything else, such as
        the answer of a social network, is escaped.

        :param notif_message: the message to display to the user.
        :param message_type: the notification type, ``danger`` by default.
        """
        if request:
            if not isinstance(notif_message, Markup):
                notif_message = escape(str(notif_message))
            request.session["social_media_notification"] = {
                "message": str(notif_message),
                "message_type": message_type,
            }

    def _format_user_notification(
        self,
        notif_message,
        media=False,
        social_name=False,
        account_name=False,
        message_type="danger",
    ):
        """Build the message of a social media notification.

        :param notif_message: the message to display to the user.
        :param media: media type to prefix the message with. Without it there
            is nothing to notify.
        :param social_name: social media name to append to the media type.
        :param account_name: account name shown instead of the media name.
        :param message_type: the notification type, ``danger`` by default.
        :rtype: markupsafe.Markup
        """
        if not media:
            return Markup()
        social_media_name = (
            media.upper() + " " + social_name if social_name else media.upper()
        )
        return Markup(
            _(
                "Social Media %(social_media)s <b> "
                "[%(account)s] </b> <br><br> %(message)s"
            )
        ) % {
            "social_media": social_media_name,
            "account": social_media_name if not account_name else account_name,
            "message": Markup("<b>%s</b> %s")
            % (
                "ERROR:" if message_type == "danger" else "",
                notif_message or "",
            ),
        }

    def _notify_user_client(
        self,
        target=None,
        notif_type=None,
        notif_message=None,
        media=False,
        social_name=False,
        account_name=False,
    ):
        """Notify the user of an event through the bus.

        :param target: partner to notify, the current user by default.
        :param notif_type: bus notification type, ``danger`` by default.
        :param notif_message: the message to display to the user.
        :param media: media type to prefix the message with.
        :param social_name: social media name to append to the media type.
        :param account_name: account name shown instead of the media name.
        """
        message_type = notif_type.split("_")[-1] if notif_type else "danger"
        message = self._format_user_notification(
            notif_message,
            media=media,
            social_name=social_name,
            account_name=account_name,
            message_type=message_type,
        )

        if message:
            self.env["bus.bus"]._sendone(
                target or self.env.user.partner_id,
                notif_type,
                {
                    "message_type": message_type,
                    "message": message,
                },
            )
