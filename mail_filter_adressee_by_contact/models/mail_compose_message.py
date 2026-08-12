# Copyright (C) 2021 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposer(models.TransientModel):
    _name = "mail.compose.message"
    _inherit = ["mail.compose.message", "mail.filter.addressee.mixin"]

    def _get_domain_for_sale_order(self, records):
        return [
            "|",
            "|",
            "|",
            ("id", "child_of", records.partner_id.commercial_partner_id.ids),
            ("id", "child_of", records.partner_invoice_id.ids),
            ("id", "child_of", records.partner_shipping_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]

    def _get_domain_for_purchase_order(self, records):
        return [
            "|",
            ("id", "child_of", records.partner_id.commercial_partner_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]

    def _get_domain_for_stock_picking(self, records):
        return [
            "|",
            ("id", "child_of", records.partner_id.commercial_partner_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]
