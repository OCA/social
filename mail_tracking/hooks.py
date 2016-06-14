# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from openerp import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        # Recalculate all partner tracking_email_ids
        partners = env['res.partner'].search([
            ('email', '!=', False),
        ])
        emails = partners.mapped('email')
        _logger.info(
            "Recalculating 'tracking_email_ids' in 'res.partner' "
            "model for %d email addresses", len(emails))
        for email in emails:
            env['mail.tracking.email'].tracking_ids_recalculate(
                'res.partner', 'email', 'tracking_email_ids', email)
