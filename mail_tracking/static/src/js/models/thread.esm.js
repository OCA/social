/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    recordMethods: {
        async refreshMessagefailed() {
            var id = this.__values.id;
            var model = this.__values.model;
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
            const messagefailed = this.messaging.models.MessageFailed.insert(
                messagefailedData.map((messageData) =>
                    this.messaging.models.MessageFailed.convertData(messageData)
                )
            );
            this.update({
                messagefailed: [["replace", messagefailed]],
            });
        },
    },
    fields: {
        messagefailed: many("MessageFailed", {
            related: "mailbox.messagefailed",
        }),
    },
});
