# Copyright 2018-22 ForgeFlow <http://www.forgeflow.com>
# Copyright 2018 Odoo, S.A.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).


def pre_init_hook(cr):
    """The objective of this hook is to default to false all values of field
    'done' of mail.activity
    """
    cr.execute(
        """SELECT column_name
    FROM information_schema.columns
    WHERE table_name='mail_activity' AND
    column_name='done'"""
    )
    if not cr.fetchone():
        cr.execute(
            """
            ALTER TABLE mail_activity ADD COLUMN done boolean;
            """
        )

    cr.execute(
        """
        UPDATE mail_activity
        SET done = False
        """
    )


def uninstall_hook(cr, registry):
    """The objective of this hook is to remove all activities that are done
    upon module uninstall
    """
    cr.execute(
        """
        DELETE FROM mail_activity
        WHERE done=True
        """
    )
