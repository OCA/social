odoo.define("mail_quoted_reply/static/src/models/mail_message_reply.js", function (
    require
) {
    "use strict";

    const {registerInstancePatchModel} = require("mail/static/src/model/model_core.js");

    registerInstancePatchModel(
        "mail.message",
        "mail_quoted_reply/static/src/models/mail_message_reply.js",
        {
            _onClickMailMessageReply: function () {
                var self = this,
                    msg_id = this.id;
                this.env.services
                    .rpc({
                        model: "mail.message",
                        method: "reply_message",
                        args: [msg_id],
                    })
                    .then(function (result) {
                        self.env.bus.trigger("do-action", {
                            action: result,
                            options: {
                                on_close: () => {
                                    self.originThread.refresh();
                                },
                            },
                        });
                    });
            },
        }
    );
});
