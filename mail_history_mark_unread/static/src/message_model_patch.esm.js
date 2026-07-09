import {Message} from "@mail/core/common/message_model";
import {patch} from "@web/core/utils/patch";

patch(Message.prototype, {
    /**
     * Mark this message as unread for the current user.
     * This moves the message from History back to Inbox and is the inverse
     * of the core setDone().
     */
    async setUndone() {
        await this.store.env.services.orm.silent.call(
            "mail.message",
            "set_message_undone",
            [[this.id]]
        );
    },
});
