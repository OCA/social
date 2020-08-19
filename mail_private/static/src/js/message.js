/* Copyright 2020 Creu Blanca
     License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */

odoo.define('mail_private.model.Message', function (require) {
    "use strict";

    var Message = require('mail.model.Message');

    var Message_Private = Message.include({
        init: function (parent, data, emojis) {
            this._super.apply(this, arguments);
            this.private = data.private || false;
            this.mail_group_id = data.mail_group_id || false;
            this.mail_group = data.mail_group || false;
        },
    });

    return Message_Private;

});
