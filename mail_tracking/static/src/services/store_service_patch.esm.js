import {Store} from "@mail/core/common/store_service";
import {Record} from "@mail/core/common/record";
import {rpc} from "@web/core/network/rpc";
import {patch} from "@web/core/utils/patch";
import {_t} from "@web/core/l10n/translation";

// As in the original
const FETCH_LIMIT = 30;

const StoreServicePatch = {
    setup() {
        super.setup(...arguments);
        this.failed = Record.one("Thread");
    },

    onStarted() {
        super.onStarted(...arguments);
        this.failed = {
            id: "failed",
            model: "mail.box",
            name: _t("Failed"),
        };
    },

    async filter_failed(thread) {
        const {data} = await rpc(thread.getFetchRoute(), {
            ...thread.getFetchParams(),
        });

        const messages = data["mail.message"].filter(
            (message) => message.is_failed_message
        );

        const count = messages?.length;
        return {
            count,
            loadMore: messages.length === FETCH_LIMIT,
            messages: this.Message.insert(messages, {html: true}),
        };
    },
};

patch(Store.prototype, StoreServicePatch);
