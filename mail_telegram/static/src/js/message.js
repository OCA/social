/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_telegram.model.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');

    Message.include({
        init: function (parent, data, emojis) {
            this._super.apply(this, arguments);
            this.telegram = data.telegram || false;
            this.customer_telegram_status = data.customer_telegram_status || false;
        }
    })

});
