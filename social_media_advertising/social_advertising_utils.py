# Copyright 2026 Binhex <https://www.binhex.cloud>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

ADVERTISING_ENVIRONMENTS = [("test", "Test"), ("production", "Production")]


def _advertising_notification(message, success=True, next_action=None):
    """Return the client action that reports what an advertising call did.

    :param message: what to tell the user.
    :param success: whether the call did what it was asked for. A failure is
        drawn in red and says which accounts it could not reach.
    :param next_action: what to chain after the notification, a soft reload in
        most cases. Nothing is chained when it is not given: a view already
        showing what changed must not be reloaded on top of it.
    :rtype: dict
    """
    params = {
        "type": "success" if success else "danger",
        "message": message,
    }
    if next_action:
        params["next"] = next_action
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": params,
    }
