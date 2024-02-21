/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Notification",
    fields: {
        iconClass: {
            compute() {
                if (
                    this.notification_type === "gateway" &&
                    this.gateway_type === "whatsapp"
                ) {
                    switch (this.notification_status) {
                        case "sent":
                            return "fa fa-whatsapp";
                        case "exception":
                            return "fa fa-whatsapp text-danger";
                    }
                }
                return this._super();
            },
        },
    },
});
