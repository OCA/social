# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    (
        env["res.users"].search([])
        + env.ref("base.default_user")
        - env.ref("base.user_admin")
    ).write(
        {
            "groups_id": [(3, env.ref("mass_mailing.group_mass_mailing_user").id)],
        }
    )
