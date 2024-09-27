# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["ir.config_parameter"].set_param("mail.restrict.template.rendering", True)
    env.ref("mail.group_mail_template_editor").write(
        {
            "users": [(6, 0, env.ref("base.user_admin").ids)],
        }
    )
