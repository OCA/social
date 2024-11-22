# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import Form, common


class TestMailAttachExistingAttachmentAccount(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "Test product"})
        cls.partner = cls.env["res.partner"].create({"name": "Mr. Odoo"})
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test sale journal", "code": "TSALE", "type": "sale"}
        )
        invoice_form = Form(
            cls.env["account.move"].with_context(default_move_type="out_invoice")
        )
        invoice_form.partner_id = cls.partner
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product
        cls.invoice = invoice_form.save()
        cls.invoice.action_post()

    def test_account_invoice_send(self):
        compose = Form(
            self.env["account.invoice.send"].with_context(
                active_ids=self.invoice.ids,
                default_model=self.invoice._name,
                default_res_id=self.invoice.id,
                default_res_model=self.invoice._name,
            )
        )
        self.assertTrue(compose.can_attach_attachment)
