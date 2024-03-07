# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    # ACTION 1: Match existing contacts
    contact_model = env["mailing.contact"]
    partner_model = env["res.partner"]
    contacts = contact_model.search([("email", "!=", False)])
    _logger.info("Trying to match %d contacts to partner by email", len(contacts))
    for contact in contacts:
        partners = partner_model.search([("email", "=ilike", contact.email)], limit=1)
        if partners:
            contact.write({"partner_id": partners.id})
    # ACTION 2: Match existing statistics
    stat_model = env["mailing.trace"]
    stats = stat_model.search([("model", "!=", False), ("res_id", "!=", False)])
    _logger.info("Trying to link %d mass mailing statistics to partner", len(stats))
    stats.partner_link()
