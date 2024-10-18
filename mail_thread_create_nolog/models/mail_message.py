# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class MailMessage(models.AbstractModel):
    _inherit = "mail.message"

    def _get_message_fields(self):
        return [
            "body",
            "date",
            "message_type",
            "model",
            "res_id",
        ]

    @api.model
    def _generate_messsage(self, domain):
        # Generate a creation message only if messages are fetched for a record.
        # In that case there is no specific record implied, so no need to generate the
        # the message.
        record = self._messages_for_record(domain)
        author = record.create_uid.partner_id

        if record and record._log_access:
            creation_message = record._creation_message()
            create_message_record = self.new(
                {
                    "body": creation_message,
                    "date": record.create_date,
                    "model": record._name,
                    "res_id": record.id,
                    "message_type": "notification",
                }
            )

            data = create_message_record._read_format(
                self._get_message_fields(), load=False
            )[0]

            data.update(
                {
                    # An ID is required by the thread client-side
                    # so we generate one that doesn't really exist
                    # but based on the current thread so it'll always be
                    # unique (used by the thread_cache client model).
                    "id": self._get_create_message_id(domain),
                    # Author is not preserved above when creating the fake-record
                    "author": {
                        "id": author.id,
                        "name": author.name,
                        "type": "partner",
                    },
                }
            )

            return data

        return None

    def _get_create_message_id(self, domain):
        # Odoo JS client needs an ID to manage its cache (thread_cache).
        # Return the negative version of the greatest message ID
        # of the current record so it's always unique.
        return -self.search(domain, limit=1, order="id DESC").id

    @api.model
    def _messages_for_record(self, domain):
        """Return the record from the domain used in `message_fetch`."""
        model = res_id = None
        for part in domain:
            if len(part) == 3 and part[0] == "model" and part[1] == "=":
                model = part[2]
            if len(part) == 3 and part[0] == "res_id" and part[1] == "=":
                res_id = part[2]
            if model and res_id:
                break
        if model and res_id:
            return self.env[model].browse(res_id).exists()
        return self.browse()
