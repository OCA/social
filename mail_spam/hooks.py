# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, _):
    """Set the default Pyzor server for existing companies."""
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        Companies = env['res.company']
        Companies.search([]).write({
            'pyzor_server_ids': Companies._default_pyzor_server_ids(),
        })
