/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerModel} from "@mail/model/model_core";

registerModel({
    name: "GatewayChannelView",
    fields: {
        component: attr(),
        composerViewOwner: one("ComposerView", {
            identifying: true,
            inverse: "composerGatewayChannelView",
        }),
    },
});
