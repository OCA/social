# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Helpers shared by the connector modules of *Social Media Base*."""

import hashlib
import hmac

MEDIA_MODELS = ("social.post", "social.post.account")


def is_media_attachment(attachment):
    """Return whether an attachment is a media of a social post.

    Connectors expose public endpoints so the social networks can fetch the
    images and videos of a post while publishing it. Those endpoints must not
    hand out any other attachment of the database, so the record the
    attachment is anchored to is what tells them apart.

    :param attachment: the ``ir.attachment`` to check.
    :rtype: bool
    """
    return bool(
        attachment.exists()
        and attachment.res_id
        and attachment.res_model in MEDIA_MODELS
    )


def media_attachment_token(env, attachment_id):
    """Return the signature a public media endpoint asks for.

    The endpoints are public so the social networks can download the media,
    but an unsigned id is enumerable and would leak the media of posts that
    were never published. The signature ties the URL to the database UUID, so
    only the addresses the instance itself generated are served.

    :param env: the Odoo environment, to read the database UUID.
    :param int attachment_id: the ``ir.attachment`` id being signed.
    :rtype: str
    """
    secret = env["ir.config_parameter"].sudo().get_param("database.uuid") or ""
    return hmac.new(
        secret.encode(), str(attachment_id).encode(), hashlib.sha256
    ).hexdigest()[:32]


def is_media_request_valid(env, attachment, token):
    """Return whether a public media request may be served.

    :param env: the Odoo environment.
    :param attachment: the ``ir.attachment`` being asked for.
    :param str token: the signature the request carries.
    :rtype: bool
    """
    return is_media_attachment(attachment) and hmac.compare_digest(
        token or "", media_attachment_token(env, attachment.id)
    )
