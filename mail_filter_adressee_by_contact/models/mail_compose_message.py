# Copyright (C) 2021 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

FILTERED_MODEL = [
    "account.move",
    "sale.order",
    "purchase.order",
    "stock.picking",
]


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    partner_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_rel",
        "wizard_id",
        "partner_id",
        "Additional Contacts",
    )

    apply_filter = fields.Boolean(default=True, string="Filtering relevant adressees")

    @api.onchange("apply_filter")
    def _get_partner_ids_domain(self):
        domain = [("type", "!=", "private")]
        model = self._context.get("active_model")
        if model in FILTERED_MODEL and self.apply_filter:
            domain.insert(0, "&")
            records = self.env[self._context["active_model"]].browse(
                self._context.get("active_ids")
            )
            partners = getattr(self, f"_get_domain_for_{model.replace('.', '_')}")(
                records
            )
            domain += partners
        return {"domain": {"partner_ids": domain}}

    def _get_domain_for_sale_order(self, records):
        return [
            "|",
            "|",
            "|",
            "|",
            ("user_ids", "!=", False),
            ("id", "child_of", records.partner_id.ids),
            ("id", "child_of", records.partner_invoice_id.ids),
            ("id", "child_of", records.partner_shipping_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]

    def _get_domain_for_account_move(self, records):
        return [
            "|",
            "|",
            "|",
            ("user_ids", "!=", False),
            ("id", "child_of", records.partner_id.ids),
            ("id", "child_of", records.partner_shipping_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]

    def _get_domain_for_purchase_order(self, records):
        return [
            "|",
            "|",
            ("user_ids", "!=", False),
            ("id", "child_of", records.partner_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]

    def _get_domain_for_stock_picking(self, records):
        return [
            "|",
            "|",
            ("user_ids", "!=", False),
            ("id", "child_of", records.partner_id.ids),
            ("id", "in", records.message_partner_ids.ids),
        ]
