/* @odoo-module */

import {DiscussSidebarCategories} from "@mail/discuss/core/web/discuss_sidebar_categories";

import {patch} from "@web/core/utils/patch";

patch(DiscussSidebarCategories.prototype, {
    filteredThreads(category) {
        const threads = super.filteredThreads(category);
        if (category.id !== "channels") {
            return threads;
        }
        return threads.filter((thread) => {
            const selfMember = thread.selfMember;
            const isHidden = selfMember && selfMember.is_sidebar_hidden;
            if (!isHidden) {
                return true;
            }
            return (
                (thread.message_unread_counter || 0) > 0 ||
                (thread.message_needaction_counter || 0) > 0
            );
        });
    },

    async hideChannel(thread) {
        await this.orm.call(
            "discuss.channel",
            "action_set_sidebar_hidden",
            [[thread.id]],
            {
                hidden: true,
            }
        );
        thread.is_pinned = false;
        if (thread.selfMember) {
            thread.selfMember.is_sidebar_hidden = true;
        }
        if (thread.eq(this.store.discuss.thread)) {
            this.threadService.setDiscussThread(this.store.discuss.inbox);
        }
    },
});
