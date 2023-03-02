/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            if ("is_failed_message" in data) {
                data2.isFailed = data.is_failed_message;
            }
            return data2;
        },
    },
    fields: {
        isFailed: attr({
            default: false,
        }),
    },
});
