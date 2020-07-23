odoo.define('telegram.model.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');

    Message.include({
        init: function (parent, data) {
            this._super.apply(this, arguments);
            this.telegram_chat_id = data.telegram_chat_id || false;
            this.telegram_unread = data.telegram_unread || false;
        },
        isNeedaction: function () {
            return this._super.apply(this, arguments) || this.telegram_unread;
        },
    });

});
