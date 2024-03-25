/** @odoo-module **/
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageAction",
    fields: {
        messageActionListOwnerAsSendBroker: one("MessageActionList", {
            identifying: true,
            inverse: "actionSendBroker",
        }),
        sequence: {
            compute() {
                if (
                    this.messageActionListOwner ===
                    this.messageActionListOwnerAsSendBroker
                ) {
                    return 7;
                }
                return this._super();
            },
        },
        messageActionListOwner: {
            compute() {
                if (this.messageActionListOwnerAsSendBroker) {
                    return this.messageActionListOwnerAsSendBroker;
                }
                return this._super();
            },
        },
    },
});
