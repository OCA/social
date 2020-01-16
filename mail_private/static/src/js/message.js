/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_private.make_message', function (require) {
    "use strict";

    var chat_manager = require('mail.chat_manager');

    chat_manager._make_message_super_private = chat_manager.make_message;
    chat_manager.make_message = function (data) {
        var msg = this._make_message_super_private(data);
        msg.private = data.private || false;
        msg.mail_group_id = data.mail_group_id || false;
        msg.mail_group = data.mail_group || false;
        return msg;
    };
});
