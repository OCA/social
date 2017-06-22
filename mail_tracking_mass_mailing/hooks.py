# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
try:
    from odoo.addons.mail_tracking.hooks import column_add_with_value
except ImportError:
    column_add_with_value = False

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    if column_add_with_value:
        _logger.info("Creating mail.mass_mailing.contact.email_score column "
                     "with value 50.0")
        column_add_with_value(
            cr, 'mail_mass_mailing_contact', 'email_score', 'double precision',
            50.0)
