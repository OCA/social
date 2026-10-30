/* @odoo-module */

import {DiscussAppCategory} from "@mail/core/common/discuss_app_category_model";
import {compareDatetime} from "@mail/utils/common/misc";

import {patch} from "@web/core/utils/patch";

patch(DiscussAppCategory.prototype, {
    sortThreads(thread1, thread2) {
        if (this.id !== "channels") {
            return super.sortThreads(thread1, thread2);
        }

        const thread1Unread = thread1.message_unread_counter > 0;
        const thread2Unread = thread2.message_unread_counter > 0;

        if (thread1Unread && !thread2Unread) {
            return -1;
        }
        if (thread2Unread && !thread1Unread) {
            return 1;
        }
        if (thread1Unread && thread2Unread) {
            const thread1NewestMessage = thread1.newestPersistentNotEmptyOfAllMessage;
            const thread2NewestMessage = thread2.newestPersistentNotEmptyOfAllMessage;
            return (
                compareDatetime(
                    thread2.lastInterestDateTime,
                    thread1.lastInterestDateTime
                ) ||
                compareDatetime(
                    thread2NewestMessage && thread2NewestMessage.datetime,
                    thread1NewestMessage && thread1NewestMessage.datetime
                ) ||
                super.sortThreads(thread1, thread2)
            );
        }

        return super.sortThreads(thread1, thread2);
    },
});
