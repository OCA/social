/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_telegram.make_message', function (require) {
    "use strict";

    var chat_manager = require('mail.chat_manager');

    // Chat_manager is a simple dictionary, not an OdooClass
    chat_manager._make_message_super = chat_manager.make_message;
    chat_manager.make_message = function (data) {
        var msg = this._make_message_super(data);
        msg.telegram = data.telegram || false;
        msg.customer_telegram_status = data.customer_telegram_status || false;
        return msg;
    };

});
