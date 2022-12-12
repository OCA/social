# Copyright 2021 Camptocamp (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def _apply_default_mailing_list_values(env):
    """Apply default mailing.list values to existing records

    When the field is created by the ORM, the new mail.template records don't exist yet,
    so their values aren't set.
    """
    module = "mass_mailing_subscription_email"
    records = env["mailing.list"].search([])
    records.subscribe_template_id = env.ref(f"{module}.mailing_list_subscribe")
    records.unsubscribe_template_id = env.ref(f"{module}.mailing_list_unsubscribe")


def post_init_hook(cr, registry):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        _apply_default_mailing_list_values(env)
