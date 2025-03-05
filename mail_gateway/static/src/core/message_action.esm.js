/** @odoo-module **/
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageAction",
    fields: {
        messageActionListOwnerAsSendGateway: one("MessageActionList", {
            identifying: true,
            inverse: "actionSendGateway",
        }),
        messageActionListOwnerAsAddToThread: one("MessageActionList", {
            identifying: true,
            inverse: "actionAddToThread",
        }),
        sequence: {
            compute() {
                if (
                    this.messageActionListOwner ===
                    this.messageActionListOwnerAsSendGateway
                ) {
                    return 7;
                }
                if (
                    this.messageActionListOwner ===
                    this.messageActionListOwnerAsAddToThread
                ) {
                    return 8;
                }
                return this._super();
            },
        },
        messageActionListOwner: {
            compute() {
                if (this.messageActionListOwnerAsSendGateway) {
                    return this.messageActionListOwnerAsSendGateway;
                }
                if (this.messageActionListOwnerAsAddToThread) {
                    return this.messageActionListOwnerAsAddToThread;
                }
                return this._super();
            },
        },
    },
});
