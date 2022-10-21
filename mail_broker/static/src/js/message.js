odoo.define("mail_broker.model.Message", function(require) {
    "use strict";

    var Message = require("mail.model.Message");

    Message.include({
        init: function(parent, data) {
            this._super.apply(this, arguments);
            this.broker_channel_id = data.broker_channel_id || false;
            this.broker_unread = data.broker_unread || false;
            this.broker_type = data.broker_type || false;
            this.customer_status = data.customer_status || false;
            console.log(this);
        },
        isNeedaction: function() {
            return this._super.apply(this, arguments) || this.broker_unread;
        },
    });
});
