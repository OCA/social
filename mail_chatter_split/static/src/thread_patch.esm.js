/** @odoo-module */

import {Thread} from "@mail/core/common/thread";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    /**
     * Get messages to display, applying the chatter view mode filter if set
     * @returns {Array}
     */
    getMessagesToDisplay() {
        const thread = this.props.thread;
        if (!thread) {
            return [];
        }
        return thread.displayedMessages || thread.nonEmptyMessages;
    },
});
