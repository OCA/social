# Copyright (C) 2026 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests.common import TransactionCase


class TestMailFilterAdresseeByContact(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.partner_main = cls.env["res.partner"].create(
            {"name": "Principal Customer", "email": "client@example.com"}
        )
        cls.partner_shipping = cls.env["res.partner"].create(
            {
                "name": "delivery Adress",
                "type": "delivery",
                "parent_id": cls.partner_main.id,
                "email": "delivery@example.com",
            }
        )
        cls.partner_invoice = cls.env["res.partner"].create(
            {
                "name": "Invoice Adress",
                "type": "invoice",
                "parent_id": cls.partner_main.id,
                "email": "invoice@example.com",
            }
        )
        cls.partner_follower = cls.env["res.partner"].create(
            {"name": "follower", "email": "follower@example.com"}
        )
        cls.partner_private = cls.env["res.partner"].create({"name": "no email"})
        cls.partner_user = cls.env.ref("base.partner_admin")

        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner_main.id,
                "partner_invoice_id": cls.partner_invoice.id,
                "partner_shipping_id": cls.partner_shipping.id,
            }
        )
        cls.sale_order.message_subscribe(partner_ids=cls.partner_follower.ids)

        cls.invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": cls.partner_main.id,
                "partner_shipping_id": cls.partner_shipping.id,
                "line_ids": [
                    (0, 0, {"name": "Test Line", "quantity": 1, "price_unit": 100}),
                ],
            }
        )
        cls.invoice.message_subscribe(partner_ids=cls.partner_follower.ids)

    def _make_composer(self, active_model, active_ids, apply_filter="contacts"):
        return (
            self.env["mail.compose.message"]
            .with_context(
                active_model=active_model,
                active_ids=active_ids,
            )
            .create({"apply_filter": apply_filter})
        )

    def _make_send_wizard(self, active_ids, apply_filter="contacts"):
        context = {
            "active_model": "account.move",
            "active_ids": active_ids,
        }
        return (
            self.env["account.move.send.wizard"]
            .with_context(**context)
            .create({"apply_filter": apply_filter})
        )

    def test_composer_users_filter(self):
        composer = self._make_composer(
            "sale.order", self.sale_order.ids, apply_filter="users"
        )
        domain = composer.partner_ids_domain
        partners = self.env["res.partner"].search(domain)
        self.assertIn(self.partner_user, partners)
        self.assertNotIn(self.partner_follower, partners)
        self.assertNotIn(self.partner_private, partners)

    def test_composer_all_filter(self):
        composer = self._make_composer(
            "sale.order", self.sale_order.ids, apply_filter="all"
        )
        domain = composer.partner_ids_domain
        partners = self.env["res.partner"].search(domain)
        self.assertIn(self.partner_main, partners)
        self.assertIn(self.partner_follower, partners)
        self.assertIn(self.partner_user, partners)
        self.assertNotIn(self.partner_private, partners)

    def test_send_wizard_contacts_filter(self):
        self.invoice.action_post()
        wizard = self._make_send_wizard(self.invoice.ids)
        domain = wizard.partner_ids_domain
        partners = self.env["res.partner"].search(domain)
        self.assertIn(self.partner_main, partners)
        self.assertIn(self.partner_shipping, partners)
        self.assertIn(self.partner_follower, partners)
        self.assertNotIn(self.partner_private, partners)

    def test_send_wizard_users_filter(self):
        self.invoice.action_post()
        wizard = self._make_send_wizard(self.invoice.ids, apply_filter="users")
        domain = wizard.partner_ids_domain
        partners = self.env["res.partner"].search(domain)
        self.assertIn(self.partner_user, partners)
        self.assertNotIn(self.partner_follower, partners)
        self.assertNotIn(self.partner_private, partners)

    def test_send_wizard_all_filter(self):
        self.invoice.action_post()
        wizard = self._make_send_wizard(self.invoice.ids, apply_filter="all")
        domain = wizard.partner_ids_domain
        partners = self.env["res.partner"].search(domain)
        self.assertIn(self.partner_main, partners)
        self.assertIn(self.partner_user, partners)
        self.assertNotIn(self.partner_private, partners)
