import {assignDefined, assignIn} from "@mail/utils/common/misc";
import {Thread} from "@mail/core/common/thread_model";
import {fields} from "@mail/core/common/record";
import {patch} from "@web/core/utils/patch";
import {url} from "@web/core/utils/urls";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        if (thread.channel_type === "gateway") {
            assignIn(thread, data, ["anonymous_name", "gateway"]);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.gateway = fields.One("Gateway");
        this.operator = fields.One("res.partner");
        this.gateway_notifications = [];
        this.gateway_followers = fields.Many("res.partner");
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
