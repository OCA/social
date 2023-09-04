/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussView",
    fields: {
        failedMessageView: one("DiscussSidebarMailboxView", {
            default: {},
            inverse: "discussViewOwnerAsFailedMessage",
        }),
    },
});
