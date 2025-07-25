/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageAction",
    fields: {
        replyMessageAction: one("MessageActionList", {
            identifying: true,
            inverse: "replyMessage",
        }),
        replyAllMessageAction: one("MessageActionList", {
            identifying: true,
            inverse: "replyAllMessage",
        }),

        messageActionListOwner: {
            compute() {
                if (this.replyMessageAction) {
                    return this.replyMessageAction;
                } else if (this.replyAllMessageAction) {
                    return this.replyAllMessageAction;
                }
                return this._super();
            },
        },
        sequence: {
            compute() {
                if (this.messageActionListOwner === this.replyMessageAction) {
                    return 1;
                } else if (this.messageActionListOwner === this.replyAllMessageAction) {
                    return 2;
                }
                return this._super();
            },
        },
    },
});
