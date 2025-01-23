# Copyright 2025 Quartile
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.exceptions import AccessDenied
from odoo.service import db
from odoo.sql_db import db_connect
from odoo.tools import config

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


def update_mail_domain_blacklist(cr):
    cr.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'ir_config_parameter'
        )
        """
    )
    table_exists = cr.fetchone()[0]
    if not table_exists:
        return
    cr.execute(
        "SELECT value FROM ir_config_parameter WHERE key = %s",
        ("iap_mail_domain_blacklist.mail_domain_blacklist",),
    )
    param_value = cr.fetchone()
    if param_value and param_value[0]:
        additional_domains = {domain.strip() for domain in param_value[0].split(",")}
        iap_tools._MAIL_DOMAIN_BLACKLIST.update(additional_domains)


def _db_names():
    if config.get("db_name"):
        return [n.strip() for n in config["db_name"].split(",") if n.strip()]
    try:
        return db.list_dbs()
    except AccessDenied:
        return []


def post_load_hook():
    for db_name in _db_names():
        try:
            with db_connect(db_name).cursor() as cr:
                update_mail_domain_blacklist(cr)
        except Exception:
            _logger.error(f"Skipping database {db_name} due to an issue connecting.")
