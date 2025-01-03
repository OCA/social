# Copyright 2025 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.tools.sql import drop_constraint


def _pre_init_hook(env):
    drop_constraint(
        env.cr,
        "mail_template_ir_actions_report_rel",
        "mail_template_ir_actions_report_rel_pkey",
    )
    query = """
    ALTER TABLE mail_template_ir_actions_report_rel
    ADD COLUMN id SERIAL PRIMARY KEY;
    """
    env.cr.execute(query)
