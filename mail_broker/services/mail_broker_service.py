# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo.addons.base_rest import restapi
from odoo.addons.component.core import Component


class BrokerMethodParams(restapi.RestMethodParam):
    def from_params(self, service, params):
        return params

    def to_response(self, service, result):
        return result


class MailBrokerService(Component):
    _inherit = "base.rest.service"
    _name = "mail.broker.base.service"
    _usage = "broker"
    _collection = "mail.broker.services"

    @restapi.method(
        [(["/<string:bot_key>/update"], "GET")],
        input_param=BrokerMethodParams(),
        output_param=BrokerMethodParams(),
        auth="none",
    )
    def get_update(self, token, **kwargs):
        bot_id = self.env["mail.broker"]._get_broker_id(token, **kwargs)
        if not bot_id:
            return None
        return self.env["mail.broker"].browse(bot_id)._verify_bot(**kwargs)

    @restapi.method(
        [(["/<string:bot_key>/update"], "POST")],
        output_param=BrokerMethodParams(),
        input_param=BrokerMethodParams(),
        auth="none",
    )
    def post_update(self, token, **kwargs):
        bot_id = self.env["mail.broker"]._get_broker_id(token, **kwargs)
        if not bot_id:
            return {}
        broker = self.env["mail.broker"].browse(bot_id)
        broker.with_user(broker.webhook_user_id.id).with_context(
            notify_broker=True
        )._receive_update(kwargs)
        return {}
