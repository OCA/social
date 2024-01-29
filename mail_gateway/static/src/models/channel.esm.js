/** @odoo-module **/

import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Channel",
    fields: {
        discussSidebarCategory: {
            compute() {
                // On gateway channels we must set the right category
                if (this.thread && this.thread.gateway) {
                    const category = this.messaging.discuss.categoryGateways.filter(
                        (ctg) => ctg.gateway === this.thread.gateway
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
                // We will not set a correspondent on gateways, as it gets yourself.
                if (this.channel_type === "gateway") {
                    return clear();
                }
                return this._super();
            },
        },
    },
});
