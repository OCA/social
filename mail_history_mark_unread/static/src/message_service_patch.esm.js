/* @odoo-module */

import {MessageService} from "@mail/core/common/message_service";
import {patch} from "@web/core/utils/patch";

patch(MessageService.prototype, {
    /**
     * Mark a message as unread for the current user.
     * This moves the message from History back to Inbox.
     *
     * @param {Object} message - The message to mark as unread
     */
    async setUndone(message) {
        await this.orm.silent.call("mail.message", "set_message_undone", [
            [message.id],
        ]);
    },
});
