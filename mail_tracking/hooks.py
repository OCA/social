# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from psycopg2.extensions import AsIs

_logger = logging.getLogger(__name__)


def column_exists(cr, table, column):
    cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s""", (table, column))
    return bool(cr.fetchall())


def column_add_with_value(cr, table, column, field_type, value):
    if not column_exists(cr, table, column):
        cr.execute("""
            ALTER TABLE %s
            ADD COLUMN %s %s""", (AsIs(table), AsIs(column), AsIs(field_type)))
        cr.execute("""
            UPDATE %s SET %s = %s""", (AsIs(table), AsIs(column), value))


def pre_init_hook(cr):
    _logger.info("Creating res.partner.tracking_emails_count column "
                 "with value 0")
    column_add_with_value(
        cr, "res_partner", "tracking_emails_count", "integer", 0)
    _logger.info("Creating res.partner.email_score column "
                 "with value 50.0")
    column_add_with_value(
        cr, "res_partner", "email_score", "double precision", 50.0)
