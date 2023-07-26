/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Messaging",
    fields: {
        failedmsg: one("Mailbox", {
            default: {},
            inverse: "messagingAsFailed",
        }),
    },
});
