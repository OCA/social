odoo.define("mail_broker/static/src/js/message.js", function (require) {
    "use strict";

    const {registerClassPatchModel} = require("mail/static/src/model/model_core.js");

    registerClassPatchModel(
        "mail.message",
        "mail/static/src/models/message/message.js",
        {
            convertData(data) {
                const data2 = this._super(data);
                if ("broker_channel_id" in data) {
                    data2.broker_channel_id = data.broker_channel_id || false;
                    data2.broker_unread = data.broker_unread || false;
                    data2.broker_type = data.broker_type || false;
                    data2.customer_status = data.customer_status || false;
                    data2.isNeedaction = data2.isNeedaction || data.broker_unread;
                }
                return data2;
            },
        }
    );
});
