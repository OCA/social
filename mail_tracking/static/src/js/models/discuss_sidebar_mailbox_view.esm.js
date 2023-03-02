/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarMailboxView",
    fields: {
        discussViewOwnerAsFailedmsg: one("DiscussView", {
            identifying: true,
            inverse: "failedmsgView",
        }),
        mailbox: {
            compute() {
                if (this.discussViewOwnerAsFailedmsg) {
                    return this.messaging.failedmsg;
                }
                return this._super();
            },
        },
    },
});
