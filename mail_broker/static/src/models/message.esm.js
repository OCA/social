/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    fields: {
        broker_type: attr(),
        broker_channel_data: attr(),
        brokerThread: one("Thread", {inverse: "messagesAsBrokerThread"}),
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            data2.broker_type = data.broker_type;
            data2.broker_channel_data = data.broker_channel_data;
            if (
                data.broker_thread_data &&
                Object.keys(data.broker_thread_data).length > 0
            ) {
                data2.brokerThread = data.broker_thread_data;
            }
            return data2;
        },
    },
});
