# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openerp import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Recalculate all mass_mailing contacts tracking_email_ids
        contacts = env['mail.mass_mailing.contact'].search([
            ('email', '!=', False),
        ])
        emails = contacts.mapped('email')
        _logger.info(
            "Recalculating 'tracking_email_ids' in "
            "'mail.mass_mailing.contact' model for %d email addresses",
            len(emails))
        for n, email in enumerate(emails):
            env['mail.tracking.email'].tracking_ids_recalculate(
                'mail.mass_mailing.contact', 'email', 'tracking_email_ids',
                email)
            if n % 500 == 0:  # pragma: no cover
                _logger.info("   Recalculated %d of %d", n, len(emails))
