/** @odoo-module **/

import {attr} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessageView",
    recordMethods: {
        doNothing() {
            return true;
        },
    },
    fields: {
        isInFailedDiscuss: attr({
            compute() {
                const discuss =
                    this.messageListViewItemOwner &&
                    this.messageListViewItemOwner.messageListViewOwner.threadViewOwner
                        .threadViewer.discuss;
                return Boolean(
                    discuss &&
                        discuss.threadView.thread.mailbox &&
                        discuss.threadView.thread.mailbox.messagingAsFailed
                );
            },
        }),
        isFailedChatterMessageView: attr({
            compute() {
                return this.message.isFailedChatterMessage;
            },
        }),
    },
});
