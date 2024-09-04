/* @odoo-module */

import {Message} from "@mail/core/common/message";
import {patch} from "@web/core/utils/patch";

export const MESSAGE_TYPES = ["email", "comment"];

export const isMessageTypeValid = (type) => {
    return MESSAGE_TYPES.includes(type);
};

patch(Message, {
    components: {...Message.components},
});

patch(Message.prototype, {
    get canReply() {
        return Boolean(this.message.res_id && isMessageTypeValid(this.message.type));
    },
});
