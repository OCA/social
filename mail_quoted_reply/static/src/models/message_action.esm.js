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

        messageActionListOwner: {
            compute() {
                if (this.replyMessageAction) {
                    return this.replyMessageAction;
                }
                return this._super();
            },
        },
        sequence: {
            compute() {
                return this.messageActionListOwner === this.replyMessageAction
                    ? 1
                    : this._super();
            },
        },
    },
});
