/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        async _init(params) {
            const result = this._super(params);
            this.messaging.update({notificationTypes: params.notificationTypes});
            return result;
        },
    },
});
