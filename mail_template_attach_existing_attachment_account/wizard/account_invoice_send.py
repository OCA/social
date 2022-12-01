# Copyright 2015 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountInvoiceSend(models.TransientModel):
    _inherit = "account.invoice.send"

    @api.onchange("template_id")
    def onchange_template_id(self):
        super().onchange_template_id()
        self.composer_id._compute_object_attachment_ids()
