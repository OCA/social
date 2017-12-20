# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, _):
    """Set the default SPAM filter for existing companies."""
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        Companies = env['res.company']
        Companies.search([]).write({
            'reverend_thomas_ids': Companies._default_reverend_thomas_ids(),
        })
