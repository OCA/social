# Copyright 2023 Quartile Limited
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessageSubtype(models.Model):
    _inherit = "mail.message.subtype"

    allow_send_model_ids = fields.Many2many("ir.model")
    hide_allow_send_model = fields.Boolean(compute="_compute_hide_allow_send_model")

    def _compute_hide_allow_send_model(self):
        for rec in self:
            rec.hide_allow_send_model = rec != self.env.ref("mail.mt_comment")
