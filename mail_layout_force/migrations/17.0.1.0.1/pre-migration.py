import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Set email_layout_xmlid from the old force_email_layout_id field."""
    if not column_exists(cr, "mail_template", "force_email_layout_id"):
        _logger.info(
            "Skipping migration for mail_layout_force: "
            "old 'force_email_layout_id' column not found."
        )
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT id, force_email_layout_id
        FROM mail_template
        WHERE force_email_layout_id IS NOT NULL
    """
    )
    template_data = cr.fetchall()
    if not template_data:
        _logger.info("No mail.template records to migrate for mail_layout_force.")
        return

    _logger.info(f"Found {len(template_data)} mail.template records to migrate.")
    view_ids = [data[1] for data in template_data]
    views = env["ir.ui.view"].search_read([("id", "in", view_ids)], ["xml_id"])
    view_map = {view["id"]: view["xml_id"] for view in views}
    for template_id, view_id in template_data:
        if view_id in view_map and view_map[view_id]:
            cr.execute(
                "UPDATE mail_template SET email_layout_xmlid = %s WHERE id = %s",
                (view_map[view_id], template_id),
            )
            _logger.info(
                f"Migrated mail.template {template_id}: "
                f"set email_layout_xmlid to '{view_map[view_id]}'."
            )
    _logger.info("Migration finished for mail_layout_force.")
