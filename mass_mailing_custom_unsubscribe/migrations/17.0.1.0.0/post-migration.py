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
        INSERT INTO mailing_subscription_optout(id, name, is_feedback, sequence)
        VALUES (
            SELECT id, name, details_required, sequence
            FROM mail_unsubscription_reason
        )
    """,
    )
    # For mailing lists, get the last unsubscription for every mail and create
    # a proper mailing.subscription record
    openupgrade.logged_query(
        env.cr,
        """
        WITH latest_records AS (
            SELECT
                mu.id,
                CAST(SPLIT_PART(mu.unsubscriber_id, ',', 2) AS INTEGER) AS contact_id,
                COALESCE(mu.mailing_list_id, rel.mailing_list_id) AS list_id,
                mu.action,
                mu.reason_id,
                mu.create_uid,
                mu.write_uid,
                mu.date,
                mu.create_date,
                mu.write_date,
                mu.metadata,
                -- Window function to rank records for each contact-list pair
                ROW_NUMBER() OVER (
                    PARTITION BY
                        CAST(SPLIT_PART(mu.unsubscriber_id, ',', 2) AS INTEGER),
                        COALESCE(mu.mailing_list_id, rel.mailing_list_id)
                    ORDER BY mu.id DESC
                ) AS rn
            FROM
                mail_unsubscription mu
            LEFT JOIN
                mail_unsubscription_mailing_list_rel rel ON mu.id = rel.mail_unsubscription_id
            WHERE
                mu.unsubscriber_id LIKE 'mailing.contact,%'
                AND SPLIT_PART(mu.unsubscriber_id, ',', 2) ~ '^[0-9]+$'
                AND (mu.mailing_list_id IS NOT NULL OR rel.mailing_list_id IS NOT NULL)
                AND mu.action IN ('subscription', 'unsubscription')
        )
        INSERT INTO mailing_subscription (
            contact_id,
            list_id,
            opt_out_reason_id,
            create_uid,
            write_uid,
            opt_out,
            opt_out_datetime,
            create_date,
            write_date,
            metadata
        )
        SELECT
            contact_id,
            list_id,
            reason_id AS opt_out_reason_id,
            create_uid,
            write_uid,
            CASE
                WHEN action = 'unsubscription' THEN TRUE
                WHEN action = 'subscription' THEN FALSE
            END AS opt_out,
            CASE
                WHEN action = 'unsubscription' THEN date
                ELSE NULL
            END AS opt_out_datetime,
            create_date,
            write_date,
            metadata
        FROM
            latest_records
        WHERE
            rn = 1;  -- Only take the most recent record for each contact-list pair
        """,  # noqa: E501
    )
    # Blacklist metadata
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mail_blacklist mb
        SET metadata = latest.metadata, opt_out_reason_id = latest.reason_id
        FROM (
            SELECT DISTINCT ON (email)
                email,
                metadata,
                reason_id
            FROM
                mail_unsubscription
            WHERE
                (unsubscriber_id NOT LIKE 'mailing.contact,%' OR unsubscriber_id IS NULL)
                AND action IN ('blacklist_add', 'blacklist_rm')
                AND metadata IS NOT NULL
            ORDER BY
                email,
                id DESC  -- This ensures we get the most recent record
        ) latest
        WHERE
            mb.email = latest.email
            AND mb.metadata IS DISTINCT FROM latest.metadata
        """,  # noqa: E501
    )
    # Set the new flag Show in preferences according to the former Cross Unsubscriptable
    # value.
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE mailing_list SET is_public = NOT(not_cross_unsubscriptable)
    """,
    )
