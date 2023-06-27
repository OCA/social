/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import {many} from "@mail/model/model_field";

registerPatch({
    name: 'Thread',
    fields: {
        messagefailed: many('MailMessageFailed', {
            inverse: "thread",
        }),
    },
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
            const messagefailed = this.messaging.models["mail.message.failed"].insert(
                messagefailedData.map((messageData) =>
                    this.messaging.models["mail.message.failed"].convertData(
                        messageData
                    )
                )
            );
            this.update({
                messagefailed: [["replace", messagefailed]],
            });
        },

        _computeFetchMessagesUrl() {
            switch (this) {
                case this.messaging.failedmsg:
                    return "/mail/failed/messages";
            }
            return this._super();
        },
    }
});
