from odoo import http

from odoo.addons.website_sale.controllers.main import WebsiteSale as MailingList


class WebsiteSaleMailingListInherit(MailingList):
    @http.route(
        [
            "/shop/confirmation",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def shop_payment_confirmation(self, **post):
        response = super().shop_payment_confirmation(**post)
        order_id = response.qcontext.get("order")
        if order_id:
            order_id.sudo().subscribe_to_mailing_list()
        return response
