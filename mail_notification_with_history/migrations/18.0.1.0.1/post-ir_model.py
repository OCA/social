import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = util.env(cr)

    to_enable = []

    for model_name, model in env.registry.items():
        if getattr(model, "_mail_notification_include_history", False):
            to_enable.append(model_name)

    to_enable = env["ir.model"].search([("model", "in", to_enable)])

    if to_enable:
        to_enable.write({"include_mail_history": True})
        _logger.info(
            "Migrated mail notification with history for models: %s",
            ", ".join(to_enable.mapped("model")),
        )
