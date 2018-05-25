# Copyright 2018 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    """Ensure all existing contacts are going to work as v10"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    contacts = env['mail.mass_mailing.contact'].search([])
    for contact in contacts:
        if len(contact.list_ids) <= 1:
            continue
        list_1 = contact.list_ids[0]
        for list_ in contact.list_ids - list_1:
            contact.copy({"list_ids": [(6, 0, list_.ids)]})
        contact.list_ids = list_1
