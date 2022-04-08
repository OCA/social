odoo.define("mail_internal_chat.MailInternalChat", function(require) {
    "use strict";

    var AbstractThreadWindow = require("mail.AbstractThreadWindow");
    var Thread = require("mail.model.Thread");

    AbstractThreadWindow.include({
        _postMessage: function(messageData) {
            messageData.chat_window = true;
            return this._super.apply(this, arguments);
        },
    });

    Thread.include({
        _postMessage: function(data) {
            return this._super.apply(this, arguments).then(function(messageData) {
                if ("chat_window" in data) {
                    messageData.chat_window = data.chat_window;
                }
                return messageData;
            });
        },
    });
});
