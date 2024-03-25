/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    recordMethods: {
        onClickBrokerThread(ev) {
            ev.preventDefault();
            this.message.brokerThread.open();
        },
    },
});
