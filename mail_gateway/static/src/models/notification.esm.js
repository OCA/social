/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Notification",
    modelMethods: {
        convertData(data) {
            var data2 = this._super(data);
            data2.gateway_type = data.gateway_type;
            data2.channel_name = data.channel_name;
            return data2;
        },
    },
    fields: {
        channel_name: attr(),
        gateway_type: attr(),
    },
});
