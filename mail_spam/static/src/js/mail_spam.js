/* Copyright 2017 LasLabs Inc.
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

odoo.define('mail_spam', function(require){
    "use strict";

    var chat_manager = require('mail.chat_manager');

    // Store old method to call within the overridden
    var make_message = chat_manager.make_message;

    // Forcefully override existing make_message to inject SPAM flag
    chat_manager.make_message = function (data) {
        var message = make_message(data);
        message.is_spam = data.is_spam;
        return message;
    }

});
