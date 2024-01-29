/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerModel} from "@mail/model/model_core";

registerModel({
    name: "GatewayChannel",
    fields: {
        id: attr({identifying: true}),
        name: attr(),
        gateway: one("Gateway"),
        partner: one("Partner", {inverse: "gateway_channels"}),
    },
});
