# Copyright 2025 Hunki Enterprises BV <https://hunki-enterprises.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from psycopg2.extensions import AsIs

from odoo.addons.mail.models import mail_notification

from .models.mail_notification import index_name


def uninstall_hook(cr, registry):
    cr.execute("DROP INDEX %(index_name)s", {"index_name": AsIs(index_name)})
    cr.execute(
        """
        DELETE FROM mail_notification WHERE id in (
            SELECT id FROM (
                SELECT
                id,
                row_number() OVER (
                    PARTITION BY mail_message_id, res_partner_id
                ) AS rownum
                FROM mail_notification WHERE res_partner_id IS NOT NULL
            ) AS duplicates
            WHERE rownum > 1
        )
        """
    )
    mail_notification.MailNotification.init(
        type(
            "self",
            (object,),
            {
                "_cr": cr,
                "_table": registry["mail.notification"]._table,
                "env": type(
                    "env",
                    (object,),
                    {
                        "cr": cr,
                    },
                ),
            },
        )()
    )
