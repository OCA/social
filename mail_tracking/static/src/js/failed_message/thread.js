odoo.define("mail_tracking/static/src/js/failed_message/thread.js", function (require) {
    "use strict";

    const {
        registerInstancePatchModel,
        registerFieldPatchModel,
    } = require("mail/static/src/model/model_core.js");
    const {one2many} = require("mail/static/src/model/model_field.js");

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
                const messagefailed = this.env.models["mail.message.failed"].insert(
                    messagefailedData.map((messageData) =>
                        this.env.models["mail.message.failed"].convertData(messageData)
                    )
                );
                this.update({
                    messagefailed: [["replace", messagefailed]],
                });
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
});
