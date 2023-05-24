/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "MessagingInitializer",
    recordMethods: {
        async _init({failed_counter = 0}) {
            await this._super(...arguments);
            this._initMailboxesFailed(failed_counter);
        },

        _initMailboxesFailed(failedmsg_counter) {
            this.messaging.failedmsg.update({counter: failedmsg_counter});
        },
    },
});
