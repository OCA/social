import logging

from odoo import http
import json
_logger = logging.getLogger(__name__)


class BrokerController(http.Controller):
    @http.route(
        "/broker/<string:bot_key>/update",
        type="json",
        auth="none",
        method=["POST"],
        csrf=False,
    )
    def post_bot_updates(self, bot_key, **kwargs):
        print(kwargs)
        json_request = http.request.jsonrequest
        bot_id = http.request.env["mail.broker"]._get_broker_id(bot_key, **kwargs)
        if not bot_id:
            return {}
        broker = http.request.env["mail.broker"].browse(bot_id)
        broker.with_user(broker.webhook_user_id.id).with_context(
            notify_broker=True
        )._receive_update(json_request)
        return {}

    @http.route(
        "/braaoker/<string:bot_key>/update",
        type="http",
        auth="none",
        method=["GET"],
        csrf=False,
    )
    def get_baaot_updates(self, bot_key, **kwargs):
        # This might be used for verification
        print(kwargs)
        bot_id = http.request.env["mail.broker"]._get_broker_id(bot_key, **kwargs)
        if not bot_id:
            return ""
        return http.request.env["mail.broker"].browse(bot_id)._verify_bot(**kwargs)
