/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "DiscussSidebarMailboxView",
    recordMethods: {
        _getNonReviewedFailedMessages(messages, reviewedMessageIds) {
            if (!messages.length) return [];
            return messages.filter((message) => !reviewedMessageIds.has(message.id));
        },
    },
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
        isFailedDiscussSidebarMailboxView: attr({
            compute() {
                return Boolean(this.discussViewOwnerAsFailedMessage);
            },
        }),
    },
});
