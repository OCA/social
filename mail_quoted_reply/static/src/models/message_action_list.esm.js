/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

export const MESSAGE_TYPES = ["email", "comment"];

export const isMessageTypeValid = (type) => {
    return MESSAGE_TYPES.includes(type);
};

registerPatch({
    name: "MessageActionList",
    fields: {
        replyMessage: one("MessageAction", {
            compute() {
                if (this.message && isMessageTypeValid(this.message.message_type)) {
                    return {};
                }
                return clear();
            },
            inverse: "replyMessageAction",
        }),
    },
});
