# Copyright 2017 Tecnativa - Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
        server = self.env["fetchmail.server"].browse(
            self.env.context.get("fetchmail_server_id"))
        if server.default_thread_id and not (model or thread_id):
            model = server.default_thread_id._name
            thread_id = server.default_thread_id.id
        return super(
            MailThread,
            self.with_context(mail_create_nosubscribe=True)
        ).message_process(
            model,
            message,
            custom_values,
            save_original,
            strip_attachments,
            thread_id,
        )
