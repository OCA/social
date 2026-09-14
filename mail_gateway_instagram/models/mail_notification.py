# Copyright 2026 Cetmix OÜ
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailNotification(models.Model):
    _inherit = "mail.notification"

    instagram_sent_mids = fields.Json(
        help="Graph message_id values returned by Instagram for this send, "
        "used to skip webhook echoes of messages already posted from Odoo.",
    )
