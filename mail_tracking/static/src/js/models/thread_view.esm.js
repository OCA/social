/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "ThreadView",
    fields: {
        failedMessages: many("Message", {
            compute() {
                return this.messages.filter((message) => message.isFailed);
            },
        }),
    },
});
