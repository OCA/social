# Copyright 2025 Hunki Enterprises BV <http://hunki-enterprises.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import http

from odoo.addons.mail.controllers import discuss


class DiscussController(discuss.DiscussController):
    @http.route()
    def read_subscription_data(self, follower_id):
        result = super().read_subscription_data(follower_id)
        follower = http.request.env["mail.followers"].sudo().browse(follower_id)
        custom_notification = follower.mail_follower_custom_notification or {}
        for subtype_data in result:
            subtype_data["custom_notification"] = custom_notification.get(
                str(subtype_data["id"])
            )
        return result
