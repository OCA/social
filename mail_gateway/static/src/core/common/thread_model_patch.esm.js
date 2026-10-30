/* @odoo-module */
import {assignDefined, assignIn} from "@mail/utils/common/misc";
import {patch} from "@web/core/utils/patch";
import {Record} from "@mail/core/common/record";
import {Thread} from "@mail/core/common/thread_model";
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
        return this.type === "gateway" || super.isChatChannel;
    },
    get hasMemberList() {
        return this.type === "gateway" || super.hasMemberList;
    },
    get imgUrl() {
        if (this.type !== "gateway") {
            return super.imgUrl;
        }
        return url(
            `/discuss/channel/${this.id}/avatar_128`,
            assignDefined({}, {unique: this.avatarCacheKey})
        );
    },
    /** @param {Object} data */
    update(data) {
        super.update(data);
        if ("gateway_id" in data && this.type === "gateway") {
            this.gateway = data.gateway_id;
        }
    },
});
