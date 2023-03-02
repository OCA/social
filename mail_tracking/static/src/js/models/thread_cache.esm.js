/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "ThreadCache",
    recordMethods: {
        _extendMessageDomain(domain) {
            const thread = this.thread;
            if (thread === this.env.messaging.failedmsg) {
                return domain.concat([["is_failed_message", "=", true]]);
            }
            return this._super(...arguments);
        },
    },
});
