/* @odoo-module */

import {MailCoreWeb} from "@mail/core/web/mail_core_web_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreWeb.prototype, {
    setup() {
        super.setup(...arguments);
        this.messagingService.isReady.then(() => {
            this.busService.subscribe(
                "mail.tracking/toggle_tracking_status",
                (payload) => {
                    const {message_ids, still_failed} = payload;
                    const failed = this.store.discuss.failed;
                    for (const messageId of message_ids) {
                        const message = this.store.Message.get(messageId);
                        if (!message) {
                            continue;
                        }
                        if (!still_failed) {
                            failed.messages.delete({id: messageId});
                            failed.counter--;
                        }
                    }
                    if (failed.counter > failed.messages.length) {
                        this.threadService.fetchMoreMessages(failed);
                    }
                }
            );
            this.busService.start();
        });
    },
});
