# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    no_bounce_email = fields.Boolean(
        help="When checked, bounced emails will not be forwarded to this address"
    )
    is_automatic_reply_address = fields.Boolean(
        help="When checked, any email received from this address will not be forwarded"
        "to the followers of a conversation (chatter)",
    )
