/** @odoo-module **/

import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    recordMethods: {
        async refreshMessagefailed() {
            var id = this.__values.get("id");
            var model = this.__values.get("model");
            const messagefailedData = await this.messaging.rpc(
                {
                    model: "mail.message",
                    method: "get_failed_messsage_info",
                    args: [id, model],
                },
                {
                    shadow: true,
                }
            );
            /* Create failed Message records; these will be updated when fetching
            their usual Message data and assigned to their respective threads. */
            this.messaging.models.Message.insert(
                messagefailedData.map((messageData) =>
                    this.messaging.models.Message.convertData(
                        Object.assign(messageData, {is_failed_chatter_message: true})
                    )
                )
            );
        },
    },
});
