/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "FollowerSubtype",
    modelMethods: {
        convertData(data) {
            const result = this._super(data);
            if ("custom_notification" in data) {
                result.customNotification = data.custom_notification;
            }
            return result;
        },
    },
    fields: {
        customNotification: attr(),
    },
});
