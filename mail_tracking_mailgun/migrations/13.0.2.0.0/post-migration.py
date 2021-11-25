# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """Update webhooks.

    This version dropped support for legacy webhooks and added support for
    webhook autoregistering. Do that process now.
    """
    settings = env["res.config.settings"].create({})
    if not settings.mail_tracking_mailgun_enabled:
        _logger.warning("Not updating webhooks because mailgun is not configured")
        return
    _logger.info("Updating mailgun webhooks")
    try:
        settings.mail_tracking_mailgun_unregister_webhooks()
        settings.mail_tracking_mailgun_register_webhooks()
    except Exception:
        # Don't fail the update if you can't register webhooks; it can be a
        # failing network condition or air-gapped upgrade, and that's OK, you
        # can just update them later
        _logger.warning(
            "Failed to update mailgun webhooks; do that manually", exc_info=True
        )
