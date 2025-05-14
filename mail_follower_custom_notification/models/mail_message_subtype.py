# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailMessageSubtype(models.Model):
    _inherit = "mail.message.subtype"

    mail_follower_custom_notification = fields.Selection(
        selection=lambda self: self.env["res.users"]
        ._fields["notification_type"]
        ._description_selection(self.env),
        string="Custom notification",
        help="Override users' default notification settings for this message type",
    )
    mail_follower_custom_notification_model_ids = fields.Many2many(
        "ir.model",
        string="Models",
        help="Choose for which models the "
        "custom configuration applies. This is only necessary if your subtype "
        "doesn't set a model itself",
        domain=[("transient", "=", False)],
    )
