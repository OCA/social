# Copyright 2025 Hunki Enterprises BV <https://hunki-enterprises.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import string

from psycopg2.extensions import AsIs

from odoo import models


def remove_ws(definition):
    return "".join(filter(lambda x: x not in string.whitespace, definition))


index_name = "unique_mail_message_id_res_partner_id_if_set"
index_definition = """
CREATE UNIQUE INDEX unique_mail_message_id_res_partner_id_if_set
ON public.mail_notification
USING btree (mail_message_id, res_partner_id, notification_type)
WHERE (res_partner_id IS NOT NULL)
"""


class MailNotification(models.Model):
    _inherit = "mail.notification"

    def init(self):
        result = super().init()
        existing_definition = None
        self.env.cr.execute(
            """
            SELECT pg_get_indexdef(oid) FROM pg_class
            WHERE relname=%(index_name)s
            """,
            {"index_name": index_name},
        )
        for (existing_definition,) in self.env.cr.fetchall():
            if remove_ws(index_definition) != remove_ws(existing_definition):
                existing_definition = False

        if not existing_definition:
            self.env.cr.execute(
                "DROP INDEX %(index_name)s", {"index_name": AsIs(index_name)}
            )
            self.env.cr.execute(index_definition)
        return result
