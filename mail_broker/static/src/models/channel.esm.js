/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Channel",
    fields: {
        discussSidebarCategory: {
            compute() {
                // On broker channels we must set the right category
                if (this.thread && this.thread.broker_id) {
                    const category = this.messaging.discuss.categoryBrokers.filter(
                        (ctg) => ctg.broker_id === this.thread.broker_id
                    );
                    if (category.length > 0) {
                        return category[0];
                    }
                }
                return this._super();
            },
        },
        correspondent: {
            compute() {
                // We will not set a correspondent on brokers, as it gets yourself.
                if (this.channel_type === "broker") {
                    return clear();
                }
                return this._super();
            },
        },
    },
});
