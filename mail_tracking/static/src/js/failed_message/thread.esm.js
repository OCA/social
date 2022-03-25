/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from "@mail/model/model_core";
import {one2many} from "@mail/model/model_field";

registerInstancePatchModel(
    "mail.thread",
    "mail_tracking/static/src/js/failed_message/thread.js",
    {
        async refreshMessagefailed() {
            var id = this.__values.id;
            var model = this.__values.model;
            const messagefailedData = await this.async(() =>
                this.env.services.rpc(
                    {
                        model: "mail.message",
                        method: "get_failed_messsage_info",
                        args: [id, model],
                    },
                    {
                        shadow: true,
                    }
                )
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
);

registerFieldPatchModel(
    "mail.thread",
    "mail_tracking/static/src/js/failed_message/thread.js",
    {
        messagefailed: one2many("mail.message.failed", {
            inverse: "thread",
        }),
    }
);
