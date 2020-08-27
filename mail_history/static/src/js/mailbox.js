/* Copyright 2020 Tecnativa - Carlos Roca
   License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). */
odoo.define('mail_history.Mailbox', function (require) {
    "use strict";

    var Mailbox = require('mail.model.Mailbox');

    Mailbox.include({

        /**
         * @override
         * @private
         * @returns {Array}
         * @throws on missing domain for the provided mailbox (mailboxes should
         *   always have a domain on messages to fetch)
         */
        _getThreadDomain: function () {
            if (this._id === 'mailbox_history') {
                return [['needaction', '=', false]];
            }
            return this._super.apply(this, arguments);
        },
    });
});
