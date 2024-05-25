/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    recordMethods: {
        onClickGatewayThread(ev) {
            ev.preventDefault();
            this.message.gatewayThread.open();
        },
    },
});
