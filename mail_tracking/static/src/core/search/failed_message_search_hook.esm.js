import {onWillUnmount, useState} from "@odoo/owl";
import {useSequential} from "@mail/utils/common/hooks";
import {useService} from "@web/core/utils/hooks";

export function useFailedMessageSearch(thread) {
    const store = useService("mail.store");
    const sequential = useSequential();
    const state = useState({
        thread,
        async filter_failed() {
            this.searching = true;
            const {count, loadMore, messages} = await sequential(() =>
                store.filter_failed(this.thread)
            );
            this.searched = true;
            this.searching = false;
            this.count = count;
            this.loadMore = loadMore;
            this.messages = messages;
        },
        count: 0,
        clear() {
            this.messages = [];
            this.searched = false;
            this.searching = false;
            this.searchTerm = undefined;
        },
        loadMore: false,
        /** @type {import('@mail/core/common/message_model').Message[]} */
        messages: [],
        /** @type {string|undefined} */
        searchTerm: undefined,
        searched: false,
        searching: false,
        // Disabled as we won't use it
        // eslint-disable-next-line no-empty-function
        highlight: () => {},
    });
    onWillUnmount(() => {
        state.clear();
    });
    return state;
}
