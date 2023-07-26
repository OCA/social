/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarMailboxView",
    fields: {
        discussViewOwnerAsFailedMessage: one("DiscussView", {
            identifying: true,
            inverse: "failedMessageView",
        }),
        mailbox: {
            compute() {
                if (this.discussViewOwnerAsFailedMessage) {
                    return this.messaging.failedmsg;
                }
                return this._super();
            },
        },
    },
});
