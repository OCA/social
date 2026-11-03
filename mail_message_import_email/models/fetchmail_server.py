# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models

# Context key of the receiving channel that opened the form of a new server.
CHANNEL_CONTEXT_KEY = "mail_message_import_channel_id"
# Context key of a new server created from a receiving channel.
SERVER_CONTEXT_KEY = "mail_message_import_mail_server"


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    @api.model
    def default_get(self, fields_list):
        """A server created from a receiving channel reads its mailbox with IMAP
        over SSL and creates received messages, with their attachments."""
        defaults = super().default_get(fields_list)
        if not self.env.context.get(SERVER_CONTEXT_KEY):
            return defaults
        values = {
            "server_type": "imap",
            "is_ssl": True,
            "port": 993,
            "object_id": self.env["ir.model"]._get_id("mail.message.import.message"),
            "attach": True,
        }
        for name, value in values.items():
            if name in fields_list and f"default_{name}" not in self.env.context:
                defaults[name] = value
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        servers = super().create(vals_list)
        channel = self.env["mail.message.import.channel"].browse(
            self.env.context.get(CHANNEL_CONTEXT_KEY)
        )
        if len(servers) == 1 and channel.exists():
            if not channel.fetchmail_server_id:
                channel.fetchmail_server_id = servers
        return servers
