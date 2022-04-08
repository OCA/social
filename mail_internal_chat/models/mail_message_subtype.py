# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class MailMessageSubtype(models.Model):

    _inherit = "mail.message.subtype"

    keep_chat_internal = fields.Boolean(
        help="Mark this to ensure no messages sent through chat window are sent"
        " to external followers."
    )
