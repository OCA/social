# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import AbstractComponent


class BrokerMethodParams(restapi.RestMethodParam):
    def from_params(self, service, params):
        return params

    def to_response(self, service, result):
        return result

    def to_openapi_requestbody(self, service):
        return {"content": {}}

    def to_openapi_responses(self, service):
        return {"200": {"content": {}}}


class MailBrokerService(AbstractComponent):
    _inherit = "base.rest.service"
    _name = "mail.broker.base.service"
    _usage = "broker"
    _collection = "mail.broker"
    _description = "Mail Broker Services"

    @restapi.method(
        [(["/<string:bot_key>/update"], "POST")],
        # output_param=BrokerMethodParams(),
        input_param=BrokerMethodParams(),
        auth="none",
    )
    def post_update(self, token, **kwargs):
        """Post an update from an external service"""
        bot_data = self.env["mail.broker"]._get_broker(
            token, broker_type=self._usage, state="integrated", **kwargs
        )
        if not bot_data:
            return {}
        if not self._verify_update(bot_data, kwargs):
            return {}
        self.collection.env = self.env(user=bot_data["webhook_user_id"])
        broker = self.env["mail.broker"].browse(bot_data["id"])
        self._receive_update(broker.with_context(notify_broker=True), kwargs)
        return False

    def _verify_update(self, bot_data, kwargs):
        return True

    def _receive_update(self, broker, kwargs):
        pass

    def _set_webhook(self):
        self.collection.integrated_webhook_state = "integrated"

    def _remove_webhook(self):
        self.collection.integrated_webhook_state = False

    def _get_channel(self, broker, token, update, force_create=False):
        chat_id = broker._get_channel_id(token)
        if chat_id:
            return self.env["mail.broker.channel"].browse(chat_id)
        if not force_create and broker.has_new_channel_security:
            return False
        return self.env["mail.broker.channel"].create(
            self._get_channel_vals(broker, token, update)
        )

    def _get_channel_vals(self, broker, token, update):
        return {
            "token": token,
            "broker_id": broker.id,
            "show_on_app": broker.show_on_app,
        }

    def _send(self, record, auto_commit=False, raise_exception=False, parse_mode=False):
        raise NotImplementedError()
