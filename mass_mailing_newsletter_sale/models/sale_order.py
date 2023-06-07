from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def subscribe_to_mailing_list(self):
        self.ensure_one()
        IrDefault = self.env["ir.default"].sudo()
        mailing_list = IrDefault.get("res.config.settings", "sale_mailing_list_id")
        if mailing_list:
            mailing_contact = self.env["mailing.contact"]
            mail = self.partner_id.email
            name = self.partner_id.name
            if not mailing_contact.search([("email", "=", mail)]):
                mailing_contact.create(
                    {"name": name, "email": mail, "list_ids": [(4, mailing_list)]}
                )
