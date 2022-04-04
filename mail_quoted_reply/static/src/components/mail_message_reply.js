odoo.define("mail_quoted_reply/static/src/components/mail_message_reply.js", function (
    require
) {
    "use strict";

    const components = {
        Message: require("mail/static/src/components/message/message.js"),
    };
    const {patch} = require("web.utils");

    patch(
        components.Message,
        "mail_quoted_reply/static/src/models/mail_message_reply.js",
        {
            _onClickMailMessageReply() {
                this.message._onClickMailMessageReply();
            },
        }
    );
});
