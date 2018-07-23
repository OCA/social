# -*- coding: utf-8 -*-
# Copyright 2018 Tecnativa <https://www.tecnativa.com>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import logging


_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    """
    This pre-creates before ORM related computation the field `res_model`,
    for avoiding an error when writing back the value on virtual records
    created by recurring events. No need of writing any possible value, as
    this is a new feature not available in v10.
    See https://github.com/OCA/OpenUpgrade/blob/11.0/addons/calendar
    /migrations/11.0.1.0/pre-migration.py
    """
    _logger.info('Pre-creating column res_model in table calendar_event')

    cr.execute("""SELECT column_name
        FROM information_schema.columns
        WHERE table_name='calendar_event' AND
        column_name='res_model'""")
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE calendar_event
            ADD COLUMN res_model
            character varying;
            COMMENT ON COLUMN calendar_event.res_model
            IS 'Document Model Name';
            """)
