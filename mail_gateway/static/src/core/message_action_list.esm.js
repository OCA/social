/** @odoo-module **/
import {clear} from "@mail/model/model_field_command";
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageActionList",
    fields: {
        actionSendGateway: one("MessageAction", {
            compute() {
                if (
                    this.message &&
                    this.message.gateway_channel_data &&
                    this.message.gateway_channel_data.partners &&
                    Object.keys(this.message.gateway_channel_data.partners).length
                ) {
                    return {};
                }
                return clear();
            },
            inverse: "messageActionListOwnerAsSendGateway",
        }),
        actionAddToThread: one("MessageAction", {
            compute() {
                if (
                    this.message.gateway_type &&
                    !this.message.gatewayThread &&
                    this.message.originThread.model === "mail.channel"
                ) {
                    return {};
                }
                return clear();
            },
            inverse: "messageActionListOwnerAsAddToThread",
        }),
    },
});
