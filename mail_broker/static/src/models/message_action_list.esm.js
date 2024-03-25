/** @odoo-module **/
import {clear} from "@mail/model/model_field_command";
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageActionList",
    fields: {
        actionSendBroker: one("MessageAction", {
            compute() {
                if (
                    this.message &&
                    this.message.broker_channel_data &&
                    this.message.broker_channel_data.partners &&
                    Object.keys(this.message.broker_channel_data.partners).length
                ) {
                    return {};
                }
                return clear();
            },
            inverse: "messageActionListOwnerAsSendBroker",
        }),
    },
});
