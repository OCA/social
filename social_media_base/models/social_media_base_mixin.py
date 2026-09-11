# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup, escape

from odoo import _, models
from odoo.http import request


class SocialMediaBaseMixin(models.AbstractModel):
    """Notify the user about what happens on the social media side.

    Any model that talks to a social media (``social.media``,
    ``social.account`` and the association wizards of the connectors) inherits
    this mixin to report the outcome to the user, be it the answer of the
    network or an error raised while reaching it::

        class SocialAccount(models.Model):
            _name = "social.account"
            _inherit = ["social.media.base.mixin"]

    There are two delivery channels and they are not interchangeable:

    * ``_notify_user_client()`` pushes the message through ``bus.bus``, and is
      the one to use for anything triggered from the web client.
    * ``_notify_user_session()`` stores it in the session so it is shown on the
      next page load. OAuth callbacks answer with a redirect that reloads the
      web client, so a bus message sent there would race with it and be lost.

    Code reached from both, such as anything an association does on the
    account it just linked, calls ``_notify_user()`` instead: it takes the
    session when the context carries ``social_media_oauth_callback`` and the
    bus otherwise, so the caller does not have to know how it was reached.

    Both render the message as markup on the client, so anything that is not
    already a ``Markup`` is escaped. ``_format_user_notification()`` builds
    that markup, prefixing the message with the social media and the account
    it refers to; it is called by ``_notify_user_client()`` and can be called
    directly to compose the message given to ``_notify_user_session()``.
    """

    _name = "social.media.base.mixin"
    _description = "User Notifications About Social Media"

    def _notify_user_session(self, notif_message, message_type="danger"):
        """Keep a message in the session until the web client is loaded again.

        The OAuth callbacks answer with a redirect, so a message sent
        through the bus at that moment never reaches the user. These ones
        are delivered by ``ir.http.session_info`` instead.

        The messages are kept as a list and every one of them is delivered.
        A single callback has more than one thing to say: associating an
        account reads its figures on the way, and a social media refusing
        them must not silence the association that did succeed, nor the
        other way round.

        The message is rendered as markup by the web client, so only the
        messages built as ``Markup`` keep their tags: anything else, such as
        the answer of a social media, is escaped.

        :param notif_message: the message to display to the user.
        :param message_type: the notification type, ``danger`` by default.
        """
        if request:
            if not isinstance(notif_message, Markup):
                notif_message = escape(str(notif_message))
            # A new list is assigned instead of the kept one being appended
            # to: the session only notices what is written on it.
            request.session["social_media_notification"] = list(
                request.session.get("social_media_notification") or []
            ) + [
                {
                    "message": str(notif_message),
                    "message_type": message_type,
                }
            ]

    def _notify_user(
        self,
        target=None,
        notif_type=None,
        notif_message=None,
        media=False,
        social_name=False,
        account_name=False,
    ):
        """Notify the user through the channel the current request can reach.

        For code called both from the web client and from an OAuth callback,
        which answers with a redirect the bus cannot outrun. The callbacks
        mark their context with ``social_media_oauth_callback`` and everything
        under them takes the session; the crons and the ordinary actions of
        the client keep the bus.

        The arguments are the ones of :meth:`~._notify_user_client`.
        """
        if not self.env.context.get("social_media_oauth_callback"):
            return self._notify_user_client(
                target=target,
                notif_type=notif_type,
                notif_message=notif_message,
                media=media,
                social_name=social_name,
                account_name=account_name,
            )
        message_type, message = self._prepare_user_notification(
            notif_type,
            notif_message,
            media=media,
            social_name=social_name,
            account_name=account_name,
        )
        if message:
            self._notify_user_session(message, message_type=message_type)

    def _notify_association_failure(self, media):
        """Tell the user their account could not be linked.

        The generic answer of an OAuth callback that failed: the exception
        may carry the raw answer of the social media, so the user only gets
        this and the detail stays in the log. The session is the channel
        because a callback redirects, and the redirect would outrun the bus.

        :param media: media type the association was attempted on.
        """
        self._notify_user_session(
            self._format_user_notification(
                _(
                    "The account could not be associated. "
                    "Check the server log for details."
                ),
                media=media,
            )
        )

    def _prepare_user_notification(
        self,
        notif_type,
        notif_message,
        media=False,
        social_name=False,
        account_name=False,
    ):
        """Return the type and the message the two channels send.

        The bus and the session say the same thing; what differs is how it
        travels.

        :param notif_type: bus notification type, ``danger`` by default.
        :param notif_message: the message to display to the user.
        :param media: media type to prefix the message with.
        :param social_name: social media name to append to the media type.
        :param account_name: account name shown instead of the media name.
        :rtype: tuple
        """
        message_type = notif_type.split("_")[-1] if notif_type else "danger"
        return message_type, self._format_user_notification(
            notif_message,
            media=media,
            social_name=social_name,
            account_name=account_name,
            message_type=message_type,
        )

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
        message = notif_message or ""
        if message_type == "danger":
            # Only a failure is announced in bold: an empty tag was left in
            # every other message otherwise.
            message = Markup("<b>ERROR:</b> %s") % message
        return Markup(
            _(
                "Social Media %(social_media)s <b> "
                "[%(account)s] </b> <br><br> %(message)s"
            )
        ) % {
            "social_media": social_media_name,
            "account": social_media_name if not account_name else account_name,
            "message": message,
        }

    def _notify_user_client(
        self,
        target=None,
        notif_type=None,
        notif_message=None,
        media=False,
        social_name=False,
        account_name=False,
        bus_type=None,
        payload=None,
    ):
        """Notify the user of an event through the bus.

        :param target: partner to notify, the current user by default.
        :param notif_type: bus notification type, ``danger`` by default. It is
            what words the message: its last part is the kind of notice.
        :param notif_message: the message to display to the user.
        :param media: media type to prefix the message with.
        :param social_name: social media name to append to the media type.
        :param account_name: account name shown instead of the media name.
        :param bus_type: the type the message travels on, ``notif_type`` by
            default. A notice a listener of its own reads — and not the
            notification service — says the same thing on a type of its own.
        :param payload: extra keys the message carries, for a listener that
            needs to know which record the notice is about.
        """
        message_type, message = self._prepare_user_notification(
            notif_type,
            notif_message,
            media=media,
            social_name=social_name,
            account_name=account_name,
        )
        if message:
            self.env["bus.bus"]._sendone(
                target or self.env.user.partner_id,
                bus_type or notif_type,
                {
                    "message_type": message_type,
                    "message": message,
                    **(payload or {}),
                },
            )
