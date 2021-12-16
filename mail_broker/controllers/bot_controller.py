import logging

from odoo import http

_logger = logging.getLogger(__name__)


class TelegramController(http.Controller):
    @http.route(
        "/broker/<string:bot_key>/update",
        type="json",
        auth="none",
        method=["POST"],
        csrf=False,
    )
    def get_bot_updates(self, bot_key):
        json_request = http.request.jsonrequest
        bot_id = http.request.env["mail.broker"]._get_broker_id(bot_key)
        if not bot_id:
            return {}
        broker = http.request.env["mail.broker"].browse(bot_id)
        broker.with_user(broker.webhook_user_id.id).with_context(
            notify_broker=True
        )._receive_update(json_request)
        return {}
