# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Replace appearances of `opt_out` field by the new field `is_blacklisted`
    openupgrade.logged_query(
        env.cr, """
        UPDATE mail_mass_mailing_list
        SET sync_domain = replace(
            sync_domain, $$'opt_out'$$, $$'is_blacklisted'$$)
        WHERE sync_domain LIKE $$%'opt_out'%$$"""
    )
