# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class TestMailLastMessage(models.Model):
    _name = "test.mail.last.message.date"
    _description = "Test Mail Last Message Date"
    _inherit = ["mail.thread", "mail.last.message.date.mixin"]

    name = fields.Char()

    def _get_tracked_message_types(self):
        return ["email"]
