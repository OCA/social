/* @odoo-module */

import {MailCoreWeb} from "@mail/core/web/mail_core_web_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreWeb.prototype, {
    setup() {
        super.setup();
        this.busService.subscribe("mail.message/mark_as_unread", (payload) => {
            const {message_ids: messageIds, needaction_inbox_counter} = payload;
            const inbox = this.store.discuss.inbox;
            const history = this.store.discuss.history;

            for (const messageId of messageIds) {
                const message = this.store.Message.get(messageId);
                if (!message) {
                    continue;
                }
                const originThread = message.originThread;
                if (originThread && !message.isNeedaction) {
                    originThread.message_needaction_counter++;
                    originThread.needactionMessages.add(message);
                }
                if (
                    this.store.user &&
                    !message.needaction_partner_ids.includes(this.store.user.id)
                ) {
                    message.needaction_partner_ids.push(this.store.user.id);
                }
                // Move message from History to Inbox
                history.messages.delete({id: messageId});
                inbox.messages.add(message);
            }
            inbox.counter = needaction_inbox_counter;
        });
    },
});
