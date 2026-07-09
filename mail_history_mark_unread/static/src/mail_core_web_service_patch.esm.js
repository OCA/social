import {MailCoreWeb} from "@mail/core/web/mail_core_web_service";
import {patch} from "@web/core/utils/patch";

patch(MailCoreWeb.prototype, {
    setup() {
        super.setup();
        this.busService.subscribe(
            "mail.message/mark_as_unread",
            (payload, {id: notifId}) => {
                const {message_ids: messageIds, needaction_inbox_counter} = payload;
                const inbox = this.store.inbox;
                const history = this.store.history;
                for (const messageId of messageIds) {
                    const message = this.store["mail.message"].get(messageId);
                    if (!message) {
                        continue;
                    }
                    const thread = message.thread;
                    if (
                        thread &&
                        !message.needaction &&
                        notifId > thread.message_needaction_counter_bus_id
                    ) {
                        thread.message_needaction_counter++;
                        thread.message_needaction_counter_bus_id = notifId;
                    }
                    message.needaction = true;
                    // Move message from History back to Inbox
                    history.messages.delete({id: messageId});
                    inbox.messages.add(message);
                }
                if (notifId > inbox.counter_bus_id) {
                    inbox.counter = needaction_inbox_counter;
                    inbox.counter_bus_id = notifId;
                }
            }
        );
    },
});
