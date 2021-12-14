# Copyright 2021 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *kw, **kwargs):
        kwargs["email_layout_xmlid"] = "mail_unique_layout.general_mail_layout"
        return super().message_post(*kw, **kwargs)
