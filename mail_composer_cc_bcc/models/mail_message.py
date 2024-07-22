# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    recipient_cc_ids = fields.Many2many(
        "res.partner",
        "mail_message_res_partner_cc_rel",
        "mail_message_id",
        "parent_id",
        string="Cc (Partners)",
        context={"active_test": False},
    )
    recipient_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_message_res_partner_bcc_rel",
        "mail_message_id",
        "parent_id",
        string="Bcc (Partners)",
        context={"active_test": False},
    )
