# Copyright 2025 Tecnativa - Víctor Martínez
# # License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class MailBlackListMixin(models.AbstractModel):
    _inherit = "mail.thread.blacklist"

    def _message_receive_bounce(self, email, partner):
        self = self.with_context(from_message_receive_bounce=True)
        return super()._message_receive_bounce(email, partner)
