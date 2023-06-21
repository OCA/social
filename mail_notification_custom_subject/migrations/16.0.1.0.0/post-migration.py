# pylint: disable=C7902
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    env.cr.execute(
        """
        UPDATE mail_message_custom_subject
        SET subject_template=REPLACE(
                REPLACE(
                subject_template,
                '${',
                '{{'),
                '}',
                '}}'
            )
        """
    )
