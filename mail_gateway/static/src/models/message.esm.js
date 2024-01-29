/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Message",
    fields: {
        gateway_type: attr(),
        gateway_channel_data: attr(),
        gateway_thread_data: attr(),
        gatewayThread: one("Thread", {
            compute() {
                if (
                    this.gateway_thread_data &&
                    Object.keys(this.gateway_thread_data).length > 0
                ) {
                    return this.gateway_thread_data;
                }
                return clear();
            },
            inverse: "messagesAsGatewayThread",
        }),
        canBeDeleted: {
            compute() {
                if (
                    this.originThread &&
                    this.originThread.model !== "mail.channel" &&
                    this.gateway_type
                ) {
                    return true;
                }
                if (
                    this.originThread &&
                    this.originThread.model === "mail.channel" &&
                    this.gateway_type
                ) {
                    return false;
                }
                return this._super();
            },
        },
    },
    modelMethods: {
        convertData(data) {
            const data2 = this._super(data);
            data2.gateway_type = data.gateway_type;
            data2.gateway_channel_data = data.gateway_channel_data;
            data2.gateway_thread_data = data.gateway_thread_data;
            return data2;
        },
    },
    recordMethods: {
        /**
         * @private
         */
        _computeGatewayData() {
            if (
                this.gateway_thread_data &&
                Object.keys(this.gateway_thread_data).length > 0
            ) {
                this.update({gatewayThread: this.gateway_thread_data});
            } else {
                this.update({gatewayThread: clear()});
            }
        },
    },

    onChanges: [
        {
            dependencies: ["gateway_thread_data"],
            methodName: "_computeGatewayData",
        },
    ],
});
