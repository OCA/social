import {MailCoreWeb} from "@mail/core/web/mail_core_web_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreWeb.prototype, {
    setup() {
        super.setup();
        this.busService.subscribe("mail.message/mark_as_unread", (payload) => {
            const {message_ids: messageIds, needaction_inbox_counter} = payload;
            const inbox = this.store.inbox;
            const history = this.store.history;
            for (const messageId of messageIds) {
                const message = this.store["mail.message"].get(messageId);
                if (!message) {
                    continue;
                }
                const thread = message.thread;
                if (thread && !message.needaction) {
                    thread.message_needaction_counter++;
                }
                message.needaction = true;
                // Move message from History back to Inbox
                history.messages.delete({id: messageId});
                inbox.messages.add(message);
            }
            inbox.counter = needaction_inbox_counter;
        });
    },
});
