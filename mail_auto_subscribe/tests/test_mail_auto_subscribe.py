# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestMailAutoSubscribe(common.TransactionCase):
    def setUp(self):
        super(TestMailAutoSubscribe, self).setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "email": "partnercompany@example.org",
                "is_company": True,
                "parent_id": False,
            }
        )
        self.auto_subscribe_tag = self.env["res.partner.category"].create(
            {
                "name": "Invoicing subscribe",
                "auto_subscribe": True,
                "model_ids": [(6, 0, [self.env.ref("sale.model_sale_order").id])],
            }
        )
        self.no_subscribe_tag = self.env["res.partner.category"].create(
            {
                "name": "Invoicing no subscribe",
                "auto_subscribe": False,
                "model_ids": [(6, 0, [self.env.ref("sale.model_sale_order").id])],
            }
        )
        self.child_of_partner_subscribe = self.env["res.partner"].create(
            {
                "name": "Child of partner subscribe",
                "email": "subscribe_child@example.org",
                "is_company": False,
                "parent_id": self.partner.id,
                "category_id": [(4, self.auto_subscribe_tag.id)],
            }
        )
        self.child_of_partner_no_subscribe = self.env["res.partner"].create(
            {
                "name": "Child of partner no subscribe",
                "email": "no_subscribe_child@example.org",
                "is_company": False,
                "parent_id": self.partner.id,
                "category_id": [(4, self.no_subscribe_tag.id)],
            }
        )
        self.product = self.env["product.product"].create(
            {"name": "Product Test", "list_price": 100.00}
        )

    def test_subscriptions(self):
        self.sale_order = self.env["sale.order"].create(
            {"partner_id": self.partner.id, "note": "Test Subscription"}
        )
        self.env["sale.order.line"].create(
            {
                "product_id": self.product.id,
                "price_unit": 190.50,
                "product_uom_qty": 8.0,
                "order_id": self.sale_order.id,
                "name": "sales order line",
            }
        )
        self.sale_order.action_confirm()
        # Child of partner subscribe has a tag with autosubscribed enabled so
        # he should be a follower
        self.subscribed = self.sale_order.message_follower_ids.filtered(
            lambda x: x.partner_id.id == self.child_of_partner_subscribe.id
        )
        _logger.info("Unknown event type: %s" % self.sale_order.message_follower_ids)
        _logger.info("Unknown event type: %s" % self.subscribed)

        # Child of partner no subscribe has a tag with autosubscribed disabled
        # so he shouldn't be a follower
        self.no_subscribed = self.sale_order.message_follower_ids.filtered(
            lambda x: x.partner_id.id == self.child_of_partner_no_subscribe.id
        )
        self.assertTrue(self.subscribed)

        self.assertFalse(self.no_subscribed)
