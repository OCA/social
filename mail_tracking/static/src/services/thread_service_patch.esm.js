/** @odoo-module */

import {ThreadService} from "@mail/core/common/thread_service";
import {patch} from "@web/core/utils/patch";

// As in the original
const FETCH_LIMIT = 30;

/** @type {import("@mail/core/common/thread_service").ThreadService} */
const ThreadServicePatch = {
    /**
     * @param {Thread} thread
     */
    async filter_failed(thread) {
        var {messages, count} = await this.rpc(this.getFetchRoute(thread), {
            ...this.getFetchParams(thread),
        });
        messages = messages.filter((message) => {
            return message.is_failed_message;
        });
        count = messages?.length;
        return {
            count,
            loadMore: messages.length === FETCH_LIMIT,
            messages: this.store.Message.insert(messages, {html: true}),
        };
    },
};

patch(ThreadService.prototype, ThreadServicePatch);
