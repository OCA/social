/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Partner",
    fields: {
        gateway_channels: many("GatewayChannel", {inverse: "partner"}),
    },
});
