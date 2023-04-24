# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class MailMessage(models.AbstractModel):
    _inherit = "mail.message"

    @api.model
    def message_fetch(self, domain, limit=20, moderated_channel_ids=None):
        res = super().message_fetch(
            domain, limit=limit, moderated_channel_ids=moderated_channel_ids
        )
        # Generate a creation message only if messages are fetched for a record.
        # Indeed 'message_fetch' is also used to populate channels, in that
        # case there is no specific record implied, so no need to generate the
        # the message.
        record = self._messages_for_record(domain)
        if record and record._log_access and len(res) < limit:
            creation_message = record._creation_message()
            create_message_values = self.new(
                {
                    "body": creation_message,
                    "date": record.create_date,
                    "is_internal": True,
                    "model": record._name,
                    "res_id": record.id,
                    "message_type": "notification",
                    "subtype_id": self.env.ref("mail.mt_note"),
                    "author_id": record.create_uid.partner_id.id,
                }
            ).message_format()[0]
            author = record.create_uid.partner_id
            create_message_values.update(
                {
                    # An ID is required by the thread client-side
                    # so we generate one that doesn't really exist
                    # but based on the current thread so it'll always be
                    # unique (used by the thread_cache client model).
                    "id": self._get_create_message_id(domain),
                    # Author is not preserved above when creating the fake-record
                    "author_id": (author.id, author.name),
                }
            )
            res.append(create_message_values)
        return res

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
