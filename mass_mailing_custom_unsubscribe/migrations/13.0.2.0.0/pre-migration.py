# Copyright 2021 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mail_unsubscription
        SET unsubscriber_id = replace(
            unsubscriber_id, 'mail.mass_mailing.contact', 'mailing.contact'
        )
        WHERE unsubscriber_id LIKE 'mail.mass_mailing_contact%'
        """,
    )
