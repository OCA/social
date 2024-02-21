/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    fields: {
        notificationIconClassName: {
            compute() {
                if (this.message && this.message.gateway_type === "whatsapp") {
                    return "fa fa-whatsapp";
                }
                return this._super();
            },
        },
        failureNotificationIconClassName: {
            compute() {
                if (this.message && this.message.gateway_type === "whatsapp") {
                    return "fa fa-whatsapp";
                }
                return this._super();
            },
        },
    },
});
