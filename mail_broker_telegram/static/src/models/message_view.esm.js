/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    fields: {
        notificationIconClassName: {
            compute() {
                if (this.message && this.message.broker_type === "telegram") {
                    return "fa fa-paper-plane";
                }
                return this._super();
            },
        },
    },
});
