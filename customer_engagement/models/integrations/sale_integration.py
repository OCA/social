"""Sale Order Integration for Customer Engagement.

This module provides integration with Odoo's sale module,
allowing agents to view and create sales orders from conversations.
"""

from odoo import api, fields, models


class ConversationSaleIntegration(models.Model):
    """Extend conversation with sale order integration."""

    _inherit = "engage.conversation"

    # Sale order fields (computed to handle missing sale module)
    sale_order_ids = fields.One2many(
        "sale.order",
        compute="_compute_sale_orders",
        string="Sales Orders",
    )
    sale_order_count = fields.Integer(
        compute="_compute_sale_orders",
        string="Order Count",
    )
    total_sales_amount = fields.Monetary(
        compute="_compute_sale_orders",
        string="Total Sales",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_company_currency",
    )

    def _compute_company_currency(self):
        """Get company currency for monetary field."""
        for record in self:
            record.company_currency_id = self.env.company.currency_id

    @api.depends("partner_id")
    def _compute_sale_orders(self):
        """Compute sale orders for the conversation partner."""
        # Check if sale module is installed
        if "sale.order" not in self.env:
            for conv in self:
                conv.sale_order_ids = False
                conv.sale_order_count = 0
                conv.total_sales_amount = 0.0
            return

        for conv in self:
            if conv.partner_id:
                orders = self.env["sale.order"].search(
                    [
                        "|",
                        ("partner_id", "=", conv.partner_id.id),
                        ("partner_id", "child_of", conv.partner_id.id),
                    ],
                    order="date_order desc",
                    limit=20,
                )
                conv.sale_order_ids = orders
                conv.sale_order_count = len(orders)
                conv.total_sales_amount = sum(orders.mapped("amount_total"))
            else:
                conv.sale_order_ids = False
                conv.sale_order_count = 0
                conv.total_sales_amount = 0.0

    def action_view_sale_orders(self):
        """Open sale orders for this partner."""
        self.ensure_one()
        if "sale.order" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Sales module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": f"Orders - {self.partner_id.name}",
            "res_model": "sale.order",
            "view_mode": "tree,form",
            "domain": [
                "|",
                ("partner_id", "=", self.partner_id.id),
                ("partner_id", "child_of", self.partner_id.id),
            ],
            "context": {
                "default_partner_id": self.partner_id.id,
                "search_default_partner_id": self.partner_id.id,
            },
        }

    def action_create_sale_order(self):
        """Create a new sale order from this conversation."""
        self.ensure_one()
        if "sale.order" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Sales module is not installed.",
                    "type": "warning",
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": "New Sale Order",
            "res_model": "sale.order",
            "view_mode": "form",
            "context": {
                "default_partner_id": self.partner_id.id,
                "default_origin": f"Conversation {self.uuid[:8] if self.uuid else self.id}",
            },
        }

    def action_create_quotation(self):
        """Create a quotation from conversation context."""
        self.ensure_one()
        if "sale.order" not in self.env:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Module Not Installed",
                    "message": "The Sales module is not installed.",
                    "type": "warning",
                },
            }

        # Create the quotation
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_id.id,
                "origin": f"Conversation {self.uuid[:8] if self.uuid else self.id}",
            }
        )

        # Log in conversation history
        self.env["engage.conversation.history"].create(
            {
                "conversation_id": self.id,
                "event_type": "integration",
                "notes": f"Created quotation {order.name}",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": "Quotation",
            "res_model": "sale.order",
            "res_id": order.id,
            "view_mode": "form",
        }
