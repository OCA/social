# Copyright 2025 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def init_alias_entry(cr, registry):
    cr.execute(
        "UPDATE mail_alias"
        " SET alias_entry = alias_name"
        " WHERE alias_entry IS NULL AND NOT alias_name IS NULL"
    )
