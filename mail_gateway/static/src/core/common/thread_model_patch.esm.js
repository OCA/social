import {assignDefined, assignIn} from "@mail/utils/common/misc";
import {Record} from "@mail/core/common/record";
import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        if (thread.type === "gateway") {
            assignIn(thread, data, ["anonymous_name", "gateway"]);
            this.store.discuss.gateway.threads.add(thread);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.gateway = Record.one("Gateway");
        this.operator = Record.one("Persona");
        this.gateway_notifications = [];
        this.gateway_followers = Record.many("Persona");
    },
    get isChatChannel() {
        return this.channel_type === "gateway" || super.isChatChannel;
    },
    get hasMemberList() {
        return this.channel_type === "gateway" || super.hasMemberList;
    },
    get avatarUrl() {
        if (this.channel_type !== "gateway") {
            return super.avatarUrl;
        }
        return url(
            `/web/image/discuss.channel/${this.id}/avatar_128`,
            assignDefined({}, {unique: this.avatarCacheKey})
        );
    },
    /** @param {Object} data */
    update(data) {
        super.update(data);
        if ("gateway_id" in data && this.channel_type === "gateway") {
            this.gateway = data.gateway_id;
        }
    },
    _computeDiscussAppCategory() {
        if (this.channel_type === "gateway") {
            return this.store.discuss.gateway;
        }
        return super._computeDiscussAppCategory(...arguments);
    },
});
