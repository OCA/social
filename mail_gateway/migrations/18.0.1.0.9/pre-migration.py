# Copyright 2025 Tecnativa - Carlos Roca
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html)
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        DELETE FROM mail_notification mn
        USING mail_message mm
        WHERE mm.gateway_message_id = mn.mail_message_id
         AND mn.notification_type != 'gateway';
        """,
    )
