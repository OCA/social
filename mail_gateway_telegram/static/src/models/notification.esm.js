/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Notification",
    fields: {
        iconClass: {
            compute() {
                if (
                    this.notification_type === "gateway" &&
                    this.gateway_type === "telegram"
                ) {
                    switch (this.notification_status) {
                        case "sent":
                            return "fa fa-paper-plane";
                        case "exception":
                            return "fa fa-paper-plane text-danger";
                    }
                }
                return this._super();
            },
        },
    },
});
