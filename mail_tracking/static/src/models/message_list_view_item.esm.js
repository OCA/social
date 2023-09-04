/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageListViewItem",
    fields: {
        isFailedChatterMessage: attr({
            compute() {
                return this.message.isFailedChatterMessage;
            },
        }),
    },
});
