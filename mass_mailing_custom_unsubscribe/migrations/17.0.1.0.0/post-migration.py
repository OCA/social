# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Delete all the default new model reasons and choose the previous ones
    env["mailing.subscription.optout"].search([]).unlink()
    openupgrade.logged_query(
        env.cr,
        """
        INSERT INTO mailing_subscription_optout(name, is_feedback, sequence)
        VALUES (
            SELECT name, details_required, sequence
            FROM mail.unsubscription.reason
        )
    """,
    )
    # Set the new flag Show in preferences according to the former Cross Unsubscriptable
    # value.
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mailing_list SET is_public = NOT(not_cross_unsubscriptable)
    """,
    )
